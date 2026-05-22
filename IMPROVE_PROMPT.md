Since you are in Flask, can you add a check to see if the total_amount matches the sum and, if not, ask the user to "Take a photo with less glare"?

Setting max tokens to 1k and disabling reasoning on Qwen3.5-Flash model increases speed from 3 mins to 1 minute, but struggles with things like discounts (IMG_1709).

Prompt working great, but kinda slow (~1 minute, but could be due to bad lightning):
f"""### ROLE
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