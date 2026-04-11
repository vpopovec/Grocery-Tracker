import base64
import os
from groq import Groq
# Ensure your ReceiptData schema is imported for the structured output
# from .models import ReceiptData

tst_img_path = '/home/viliam/Downloads/1054d006-3e67-4857-a421-67b62134771a_processed.jpeg' #IMG_0905_problematic.jpeg'
# tst_img_path = '/home/viliam/Downloads/IMG_0905_problematic.jpeg'


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
# client = OpenAI(
#   base_url="https://openrouter.ai/api/v1",
#   api_key=os.environ.get("OPENROUTER_API_KEY"),
# )

def ocr_receipt_with_qwen_openrouter(image_bytes):
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    
    completion = client.chat.completions.create(
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


with open(tst_img_path, "rb") as f:
    image_bytes = f.read()
    

from pydantic import BaseModel

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

print(f"{repr(ReceiptData)}")

# resp = ocr_receipt_with_qwen_openrouter(image_bytes)
# print(resp)

# try:
#     import json
#     resp = json.loads(resp)
# except Exception as e:
#     print("Error", e)

# ttl = 0
# for i in resp['items']:
#     ttl+=i['price']
# print(f"{ttl=}")