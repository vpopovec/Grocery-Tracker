import base64
import os
from groq import Groq
import json
from pydantic import BaseModel
# Ensure your ReceiptData schema is imported for the structured output
# from .models import ReceiptData

tst_img_path = '/home/viliam/Downloads/203c694c-eed9-4f3d-b955-5c5b905dfdee_processed.jpg' #IMG_0905_problematic.jpeg'
# tst_img_path = '/home/viliam/Downloads/IMG_0913.jpeg'

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


def ocr_receipt_with_llama_scout(image_bytes):
    client = Groq(api_key=s.environ.get("GROQ_API_KEY"))


    # 1. Convert bytes to base64 string
    base64_image = base64.b64encode(image_bytes).decode('utf-8')

    # 2. Call the Qwen Vision model
    completion = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct", # "qwen/qwen3-32b",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Extract all items from this receipt. Return ONLY a JSON object following this schema: { 'total': float, 'date': 'YYYY-MM-DD', 'items': [{'name': str, 'price': float, 'macro_category': str}] }"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        response_format={"type": "json_object"}, # Forces JSON output
        temperature=0.1, # Keep it low for data extraction
    )

    return completion.choices[0].message.content


from openai import OpenAI

# OpenRouter setup
client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key="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",# os.environ.get("OPENROUTER_API_KEY"),
)

def ocr_receipt_with_qwen_openrouter(image_bytes):
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    
    completion = client.chat.completions.parse(
        # Use the specific Qwen 2.5 VL 72B model for high accuracy
        model="qwen/qwen3.5-flash-02-23", # "qwen/qwen2.5-vl-72b-instruct",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Return JSON: {total: float, date: YYYY-MM-DD, items: [{name: str, price: float}]}"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]
            }
        ],
        # OpenRouter helps format the response
        # response_format={"type": "json_object"}
        response_format = ReceiptData
    )
    return completion.choices[0].message.content


def ocr_receipt_with_qwen_openrouter_debug(image_bytes):
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    prompt = f"""### ROLE
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

    completion = client.chat.completions.parse(
        # Use the specific Qwen 2.5 VL 72B model for high accuracy
        model="qwen/qwen3.5-flash-02-23", # "qwen/qwen2.5-vl-72b-instruct",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]
            }
        ],
        # OpenRouter helps format the response
        # response_format={"type": "json_object"}
        response_format = ReceiptData
    )
    return completion.choices[0].message.content




with open(tst_img_path, "rb") as f:
    image_bytes = f.read()
    

# resp = ocr_receipt_with_qwen_openrouter(image_bytes)
resp = ocr_receipt_with_qwen_openrouter_debug(image_bytes)
print(resp)

try:
    import json
    resp = json.loads(resp)
except Exception as e:
    print("Error", e)

ttl = 0
for i in resp['items']:
    ttl+=i['total_price']
print(f"{ttl=}")