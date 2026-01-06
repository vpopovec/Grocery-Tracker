import re
import subprocess
import tempfile
import traceback
from config import Config
from helpers import *
from sqlite_db import Database
from person import Person
from pydantic import BaseModel
from google import genai


f_name = 'lidl_bj11.jpeg'
db = Database()
client = genai.Client(api_key=Config.GEMINI_API_KEY)


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

class ReceiptData(BaseModel):
    shop_name: str
    date: str
    items: list[ReceiptItem]
    total_amount: float


def scan_receipt_with_gemini(f_name: str) -> list:
    # Load the receipt image
    with open(f_name, "rb") as f:
        image_bytes = f.read()

    prompt = "Extract all items, the shop name, date, and total amount from this Slovak receipt. Use the provided JSON schema and ISO date format."

    # 3. Call the model with Structured Output (JSON mode)
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

    # 4. Access the parsed data directly
    print(f"{response.parsed=}")
    return response.parsed


class Receipt:

    def __init__(self, f_name):
        self.f_name = f_name
        print(f"Receipt.f_name = {f_name}")
        # TODO: Check why we use cached receipt, if we are using Gemini OCR
        # Check if raw_items are stored in cache
        # cached = get_cached_receipt(f_name)
        # if not cached:
            # cache_receipt(self.raw_items, f_name)

        self.receipt_info = scan_receipt_with_gemini(f_name)

        self.shop = self.receipt_info.shop_name
        self.shopping_date = self.receipt_info.date
        print(f"GOT SHOP: {self.shop=}")
        print(f'DATE OF SHOPPING {self.shopping_date=}')
        self.grocery_list = []

    @property
    def total(self):
        return round(sum([i['final_price'] for i in self.grocery_list]), 2)


    def process_grocery_list_with_gemini(self, items):
        for item in items:
            self.grocery_list.append({'name': item.name, 'amount': item.quantity, 'final_price': item.total_price})


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
    receipt.process_grocery_list_with_gemini(receipt.receipt_info.items)
    return receipt


def save_receipt_to_db(receipt: Receipt, person_id: int, shrunk_f_name: str) -> int:
    return db.save_receipt(receipt, person_id, shrunk_f_name)


if __name__ == '__main__':

    main()
