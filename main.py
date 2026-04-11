import json
import re
import subprocess
import time
import tempfile
import traceback
import base64
from config import Config
from helpers import *
from sqlite_db import Database
from person import Person
from pydantic import BaseModel
from google import genai
from flask import render_template, flash
from openai import OpenAI

# OpenRouter setup
client_openrouter = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key=Config.OPENROUTER_API_KEY
)

f_name = 'lidl_bj11.jpeg'
db = Database()
client = genai.Client(api_key=Config.GEMINI_API_KEY)

# Makro = široká skupina, mikro = podkategória (iba hodnoty z tohto zoznamu).
SLOVAK_TAXONOMY: dict[str, list[str]] = {
    "Čerstvé potraviny": [
        "Mliečne výrobky",
        "Pečivo a pekárenské výrobky",
        "Mäso a hydina",
        "Údeniny a salámy",
        "Ryby a morské plody",
        "Ovocie",
        "Zelenina",
        "Vajcia",
    ],
    "Trvanlivé potraviny": [
        "Cestoviny, ryža a obilniny",
        "Konzervované a pohotové jedlá",
        "Oleje, octy a dressingy",
        "Omáčky, dochucovadlá a koreniny",
        "Sladkosti a cukrovinky",
        "Snackové pochutiny a chipsy",
        "Cereálie a müsli",
        "Džemy, med a nátierky",
        "Prísady na pečenie",
        "Bezmäsité a rastlinné alternatívy",
    ],
    "Nápoje": [
        "Vody a minerálky",
        "Nealkoholické nápoje",
        "Šťavy a nektáry",
        "Káva",
        "Čaj",
        "Pivo",
        "Víno",
        "Liehoviny a destiláty",
    ],
    "Mrazené potraviny": [
        "Mrazená zelenina a ovocie",
        "Mrazené polotovary a jedlá",
        "Zmrzlina a mrazené dezerty",
    ],
    "Domácnosť": [
        "Čistiace prostriedky",
        "Papierové výrobky a utierky",
        "Sáčky, fólie a obaly",
        "Sviečky a zápalky",
    ],
    "Osobná hygiena a kozmetika": [
        "Starostlivosť o telo",
        "Starostlivosť o vlasy",
        "Ústna hygiena",
        "Kozmetika a parfuméria",
    ],
    "Zdravie a drogéria": [
        "Vitamíny a doplnky výživy",
        "Lieky bez predpisu (OTC)",
        "Hygienické potreby",
    ],
    "Pre zvieratá": [
        "Krmivo",
        "Pamlsky a doplnky pre zvieratá",
    ],
    "Ostatné": [
        "Nezaradené",
        "Textil a oblečenie",
        "Sezónne a darčekové",
    ],
}

slovak_taxonomy = json.dumps(SLOVAK_TAXONOMY, ensure_ascii=False, indent=2)


def main():
    print("Welcome to Grocery Tracker")

    # print("AUTO FILLING email tst@tst.com")
    # person = Person('tst@tst.com')

    for f_name in ['77bd6009-cb1a-47a9-8ddc-dab657ad0e85.jpeg']:
        print(f"READING {f_name=}")
        receipt = process_receipt_from_fpath(f_name)
        receipt.user_edit()
        print(f"GROCERIES: total {receipt.total}")

        print("NOT SAVING TO DB !!!")
        # db.save_receipt(receipt, person.id)


class ReceiptItem(BaseModel):
    name: str
    quantity: float
    unit_price: float
    total_price: float
    macro_category: str
    micro_category: str

class ReceiptData(BaseModel):
    shop_name: str
    date: str
    items: list[ReceiptItem]
    total_amount: float


def scan_receipt_with_qwen(f_name: str):
    # Load the receipt image
    with open(f_name, "rb") as f:
        image_bytes = f.read()
    base64_image = base64.b64encode(image_bytes).decode('utf-8')

    prompt_xml = f"""### ROLE
You are a precise Slovak financial data extraction expert.

### TASK
Extract structured data from the provided Slovak receipt image/text. 
Ensure 100% mathematical consistency and follow the taxonomy rules strictly.

### EXTRACTION RULES
1. **Discounts**:
   - If a negative price line (discount) follows an item, subtract it from that item's price.
   - If multiple discount lines follow one item, sum them all into that single item's price.
   - Do NOT create separate "item" entries for discounts unless they are general "Zľava na nákup" (Total bill discount).
2. **Categories**:
   - For every item, assign a `macro_category` and `micro_category` based ONLY on the provided taxonomy.
   - Taxonomy: {slovak_taxonomy}
3. **Shop Names**:
   - Normalize `shop_name` to exactly one of: ["Lidl", "Kaufland", "Tesco", "Billa", "Coop Jednota", "Metro", "Yeme", "dm drogerie markt", "Unknown"].
4. **Math Verification**:
   - STEP 1: Sum all extracted item `total_price` values.
   - STEP 2: Compare to the extracted `total_amount`.
   - STEP 3: If they do not match, re-examine the lines for missed discounts or quantities.

### SCHEMA
Output only a JSON object matching this structure:
{{
    "shop_name": string,
    "date": "YYYY-MM-DD",
    "items": [
        {{
            "name": string,
            "quantity": float,
            "unit_price": float,
            "total_price": float,
            "macro_category": string,
            "micro_category": string
        }}
    ],
    "total_amount": float
}}"""
    print(f"PROMPT: {prompt}")
    status_message = 'success'
    # 3. Call the model with Structured Output (JSON mode)
    try:
        t0 = time.perf_counter()
        # completion = client_openrouter.chat.completions.create(
        completion = client_openrouter.beta.chat.completions.parse(
            # Use the specific Qwen 2.5 VL 72B model for high accuracy
            model="qwen/qwen3.5-flash-02-23", # "qwen/qwen2.5-vl-72b-instruct",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_xml},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ],
            # OpenRouter helps format the response
            # response_format={"type": "json_object"}
            response_format=ReceiptData # {"type": "json_object"}
        )
        response = json.loads(completion.choices[0].message.content)
        llm_elapsed_seconds = time.perf_counter() - t0
    except Exception as e:
        if "RESOURCE_EXHAUSTED" in str(e):
            status_message = "Rate limit reached! You've used your 20 free daily requests."
            print(status_message, f"{e=}")
            # Handle the pause or alert the user here
            # return render_template("receipt.html")
        # google.genai.errors.ServerError: 503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.', 'status': 'UNAVAILABLE'}}
        elif "UNAVAILABLE" in str(e):
            status_message = "Model is currently experiencing high demand. Please try again later."
            # return render_template("receipt.html")
        else:
            print(f"An API error occurred: {traceback.format_exc()}")
            status_message = "An API error occurred"
        return '', 0, status_message

    # 4. Access the parsed data directly
    print(f"{response=}")
    print(f"llm_elapsed_seconds={llm_elapsed_seconds:.3f}")
    return response, llm_elapsed_seconds, status_message


def scan_receipt_with_gemini(f_name: str):
    # Load the receipt image
    with open(f_name, "rb") as f:
        image_bytes = f.read()

    # leads to errors: If an individual item is a discount (negative final_price), then subtract this price from the item above if possible (item price will stay positive), otherwise keep the discount as separate item.
    prompt = f"""Extract all items, the shop name, date, and total amount from this Slovak receipt. Use the provided JSON schema and ISO date format.
    If an individual item is a discount (negative price) linked to the item above, join the discount by adding the discount price to the item price. Otherwise, keep the discount as separate item.
    For each item, set macro_category to one of the top-level keys and micro_category to exactly one value from that key's list (Slovak labels as given):
```{slovak_taxonomy}```. Allowed shop_name values (use exactly this string, or "Unknown" if none match): ```["Lidl","Kaufland","Tesco","Billa","Coop Jednota","Metro","Yeme","dm drogerie markt","Unknown"]```.
    There can be two standalone "items" represnting discount for one item. 
    Make sure the sum of individual prices is equal to the total price!!!"""

    status_message = 'success'
    # 3. Call the model with Structured Output (JSON mode)
    try:
        t0 = time.perf_counter()
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                prompt,
                {"inline_data": {"mime_type": "image/jpeg", "data": image_bytes}}
            ],
            config={
                "response_mime_type": "application/json",
                "response_schema": ReceiptData,
            }
        )
        llm_elapsed_seconds = time.perf_counter() - t0
    except (genai.errors.ClientError, genai.errors.ServerError) as e:
        if "RESOURCE_EXHAUSTED" in str(e):
            status_message = "Rate limit reached! You've used your 20 free daily requests."
            print(status_message)
            # Handle the pause or alert the user here
            # return render_template("receipt.html")
        # google.genai.errors.ServerError: 503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.', 'status': 'UNAVAILABLE'}}
        elif "UNAVAILABLE" in str(e):
            status_message = "Model is currently experiencing high demand. Please try again later."
            # return render_template("receipt.html")
        else:
            print(f"An API error occurred: {traceback.format_exc()}")
            status_message = "An API error occurred"
        return '', 0, status_message

    # 4. Access the parsed data directly
    print(f"{response.parsed=}")
    print(f"llm_elapsed_seconds={llm_elapsed_seconds:.3f}")
    return response.parsed, llm_elapsed_seconds, status_message


class Receipt:

    def __init__(self, f_name):
        self.f_name = f_name
        print(f"Receipt.f_name = {f_name}")
        # TODO: Check why we use cached receipt, if we are using Gemini OCR
        # Check if raw_items are stored in cache
        # cached = get_cached_receipt(f_name)
        # if not cached:
            # cache_receipt(self.raw_items, f_name)

        # self.receipt_info, self.llm_elapsed_seconds, self.status_message = scan_receipt_with_gemini(f_name)
        self.receipt_info, self.llm_elapsed_seconds, self.status_message = scan_receipt_with_qwen(f_name)

        if self.receipt_info:
            self.shop = self.receipt_info['shop_name']
            self.shopping_date = self.receipt_info['date']
            print(f"GOT SHOP: {self.shop=}")
            print(f'DATE OF SHOPPING {self.shopping_date=}')
            self.grocery_list = []

    @property
    def total(self):
        return round(sum([i['final_price'] for i in self.grocery_list]), 2)


    def process_grocery_list(self, items):
        for item in items:
            self.grocery_list.append(
                {
                    "name": item['name'],
                    "amount": item['quantity'],
                    "final_price": item['total_price'],
                    "macro_category": item['macro_category'],
                    "micro_category": item['micro_category'],
                }
            )


    def user_edit(self):
        """
        Let user edit grocery list via nano
        :return:
        """
        # Create temp file
        f = tempfile.NamedTemporaryFile(mode='w+t', delete=False)
        # Write grocery list into temp file
        f_txt = f'{self.shop}\n{self.shopping_date}\n' + '\n'.join([json.dumps(item) for item in self.grocery_list])
        f.write(f_txt)
        f.close()

        for i in range(3):
            # Open nano editor (works only in a shell, not in IDE)
            res_code = subprocess.call(['nano', f.name])
            if res_code == 0:
                with open(f.name) as rf:
                    txt = rf.readlines()
                # Load checked items into grocery list
                try:
                    shop_name, shopping_date = [i.strip() for i in txt[:2]]
                    self.shop = shop_name
                    self.shopping_date = shopping_date
                    self.grocery_list = [json.loads(item.strip()) for item in txt[2:] if item]
                except json.decoder.JSONDecodeError:
                    print("Please use valid JSON syntax for all items")
                break
            else:
                print(f"ERROR: {res_code=}")


def process_receipt_from_fpath(f_name: str) -> Receipt:
    receipt = Receipt(f_name)
    if receipt.status_message != 'success':
        return None, receipt.status_message

    receipt.process_grocery_list(receipt.receipt_info['items'])
    return receipt, "success"


def save_receipt_to_db(receipt: Receipt, person_id: int, shrunk_f_name: str) -> int:
    return db.save_receipt(receipt, person_id, shrunk_f_name)


if __name__ == '__main__':

    main()
