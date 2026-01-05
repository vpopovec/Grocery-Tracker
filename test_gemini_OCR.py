import os
from google import genai
from pydantic import BaseModel
from typing import List

# 1. Define the structure of your data
class ReceiptItem(BaseModel):
    name: str
    quantity: str
    unit_price: float
    total_price: float

class ReceiptData(BaseModel):
    shop_name: str
    date: str
    items: List[ReceiptItem]
    total_amount: float

# 2. Initialize the Gemini Client
# Get your API key from https://aistudio.google.com/
client = genai.Client(api_key=os.environ.get('GEMINI_API_KEY'))

def extract_receipt_data(image_path: str):
    # Load the receipt image
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    prompt = "Extract all items, the shop name, date, and total amount from this Slovak receipt. Use the provided JSON schema."

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
    receipt = response.parsed
    return receipt

# Example Usage
if __name__ == "__main__":
    receipt_info = extract_receipt_data("receipts/8190c0c6-a8ad-48cb-af4c-80f118fcec71_processed.jpg")
    
    print(f"Shop: {receipt_info.shop_name}")
    print(f"Date: {receipt_info.date}")
    print("-" * 30)
    for item in receipt_info.items:
        print(f"{item.name} | {item.quantity} | {item.total_price}€")
    print("-" * 30)
    print(f"Grand Total: {receipt_info.total_amount}€")