import re
import subprocess
import tempfile
import traceback

from helpers import *
from db import Database
from person import Person
import easyocr

f_name = 'lidl_bj11.jpeg'
db = Database()


def main():
    print("Welcome to Grocery Tracker")

    print("AUTO FILLING PHONE 000")
    person = Person('000')

    # for f_name in ['lidl_bj5.jpeg', 'lidl_ba1.jpg', 'lidl_bj4.jpeg', 'lidl_close.jpg', 'yeme2.jpg', 'yeme4.jpg']:
    print(f"READING {f_name=}")
    receipt = process_receipt_from_fpath(f_name)
    receipt.user_edit()
    print(f"GROCERIES: total {receipt.total}")

    db.save_receipt(receipt, person)


class Receipt:
    reader = easyocr.Reader(['sk'], gpu=False)

    def __init__(self, f_name):
        self.f_name = f_name
        # Check if raw_items are stored in cache
        cached = get_cached_receipt(f_name)
        self.raw_items = cached or Receipt.reader.readtext(f'receipts/{f_name}')
        if not cached:
            cache_receipt(self.raw_items, f_name)
        print(f"RAW ITEMS: {self.raw_items=}")
        self.receipt_text = ''.join([el[1].lower() for el in self.raw_items])
        self.shop = get_shop(self.receipt_text)
        print(f"GOT SHOP: {self.shop=}")
        self.shopping_date = get_shopping_date(self.receipt_text)
        print(f'DATE OF SHOPPING {self.shopping_date=}')
        self.grocery_list = []

    @property
    def total(self):
        return round(sum([i['final_price'] for i in self.grocery_list]), 2)

    def preprocess_items(self):
        items, item = [], []
        start_idx = 0
        print(f"PREPROCESS ITEMS: {self.shop=}")
        if self.shop == 'lidl' or not self.shop:
            try:
                start_idx = [it[1].strip() for it in self.raw_items].index('EUR') + 1
            except ValueError:
                traceback.print_exc()
                start_idx = 0
        print(f"{start_idx=}")

        # Iterate over items, group individual items together from ALPHAS to "\d [ABE]"
        for indx, raw_item in enumerate(self.raw_items[start_idx:], start_idx):
            i_pos, i_name, _ = raw_item
            print(i_name, end='  >>  ')
            is_item_name = get_item_name(i_name)
            prev_item = self.raw_items[indx - 1] if indx else ('', '', '')

            # End of item info by receiving new item name
            # if item and items and is_item_name and not get_item_name(prev_item[1]):

            item_text = ' '.join([i[1] for i in item])
            # TODO: ALSO END if previous raw_text for the item is something like k[g]\s*[0-9,]\s*
            end_of_item = re.search(r' k[sg9] \d+(.\d{2})?', item_text, re.I)  # re.escape was not working
            end_of_discount = re.search(r'(z.ava|zaloha)( \d ks)?\s*[-~]?\d+[.,]\d+', item_text, re.I)
            print(f"{end_of_item=}", end=' >> ')
            print(f"{end_of_discount=}", end=" >> ")

            # if item and is_item_name and (not get_item_name(prev_item[1]) or end_of_item):
            if item and is_item_name and (end_of_item or end_of_discount):
                print(f"FINISHING ITEM 0: {item}")
                items.append(item)
                item = []

            item.append(raw_item)
            item_text = ' '.join([i[1] for i in item])
            # If item_text contains a known prefix (for items), empty item
            if re.search(r'[cč].bloku. \d+', item_text, re.I):
                print("CLEARING ITEM")
                item = []
            print(f"{item_text=}")
            print(f'|||| {is_item_name=} and not {get_item_name(prev_item[1])}')

            # End of item info by getting the final price
            if i_name and (re.search(r'\d [ABCE]', i_name[-3:], re.I) or re.search(r'[0-9,]+\s*[ABCE]$', item_text, re.I)):
                if item:
                    print(f"FINISHING ITEM 1: {item}")
                    items.append(item)
                item = []

        # Remove prefixes from 1st item
        # if items and (prefix_and_item := re.split(r'c.bloku. \d{4} ', items[0])):
        #     print(f"PREFIX AND ITEM {prefix_and_item[1]}")
        return items

    def process_grocery_list(self, items):
        for item_indx, item in enumerate(items):
            raw_text = ' '.join([i[1] for i in item])
            # Make Ks, KG etc. lowercase
            raw_text = re.sub('( k[sg])', lambda pat: pat.group(1).lower(), raw_text, flags=re.I)
            raw_text = re.sub('( k9)', ' kg', raw_text)

            print(f"UNFILTERED: {raw_text}")
            if (' ks' not in raw_text and ' kg' not in raw_text) or is_discount(raw_text):
                continue
            print(f"RAW TEXT: {raw_text}")

            amount = amount_raw = ''
            is_pcs = ' ks' in raw_text
            is_kg = ' kg' in raw_text
            if is_pcs:
                # 0-9io are possible digits
                try:
                    amount_raw = re.search(r'.*\s+([0-9io{]{,3})\s+ks', raw_text, flags=re.IGNORECASE).group(1)
                except AttributeError:  # missing pcs info
                    print(f"Couldn't extract pcs info for {raw_text}, defaulting amount to 1")
                amount = fix_amount_int(amount_raw) if amount_raw else 1  # Defaults to 1 if it can't find num

            elif is_kg:
                amount_raw = re.search(r'(\d+,\d+)\s+kg', raw_text).group(1)
                amount = float_sk(amount_raw)

            split_parts = re.split(rf'{amount_raw}\s+k[gs]', raw_text)
            print(f"{split_parts=}")
            i_name, prices = split_parts[0], split_parts[-1]
            i_name = fix_item_name(i_name)

            try:
                # if self.shop == 'yeme':
                #     final_price = float_sk(re.search(r'\d+,\d+ (\d+,\d{2})', prices).group(1))  # first float is price per kg
                #     self.grocery_list.append({'name': i_name, 'amount': amount, 'final_price': final_price})

                if self.shop in ['lidl', 'kaufland', 'yeme'] or not self.shop:
                    sub_price = get_sub_price(prices, is_pcs)

                    next_item = items[item_indx + 1] if item_indx + 1 < len(items) else []
                    discount = get_discount_from_item(next_item)
                    print(f"{amount=} {sub_price=} {discount=}")
                    final_price = round(amount * sub_price - discount, 2)

                    self.grocery_list.append({'name': i_name, 'amount': amount, 'final_price': final_price})

            except Exception as e:
                traceback.print_exc()
                print(f"Error processing {raw_text} {e}")

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
    items = receipt.preprocess_items()
    receipt.process_grocery_list(items)
    return receipt


if __name__ == '__main__':

    main()
