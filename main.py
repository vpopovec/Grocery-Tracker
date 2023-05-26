from helpers import *
import easyocr
# f_name = 'lidl_ba1.jpg'
f_name = 'lidl_bj1.jpeg'


def main():
    print(f"READING {f_name=}")
    receipt = Receipt(f_name)
    items = receipt.preprocess_items()
    receipt.process_grocery_list(items)
    print(f"GROCERIES: total {receipt.total}")
    for grocery_item in receipt.grocery_list:
        print(grocery_item)


class Receipt:
    reader = easyocr.Reader(['sk'], gpu=False)
    
    def __init__(self, f_name):
        self.f_name = f_name
        self.raw_items = Receipt.reader.readtext(f'receipts/{f_name}')  # run only once to load the model into memory
        self.receipt_text = ''.join([el[1].lower() for el in self.raw_items])
        self.shop = get_shop(self.receipt_text)
        print(f"GOT SHOP: {self.shop=} FROM FUNC:{get_shop(self.receipt_text)}")
        self.date_of_shopping = get_date_of_shopping(self.receipt_text)
        print(f'DATE OF SHOPPING {self.date_of_shopping=}')
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
        print(f"RAW ITEMS: {self.raw_items[start_idx:]}")
        # Iterate over items, group individual items together from ALPHAS to "\d [ABE]"
        for indx, raw_item in enumerate(self.raw_items[start_idx:]):
            i_pos, i_name, _ = raw_item
            print(i_name, end='  >>  ')
            is_item_name = get_item_name(i_name)
            prev_item = self.raw_items[indx - 1] if indx else ('', '', '')

            # End of item info by receiving new item name
            if item and items and is_item_name and not get_item_name(prev_item[1]):
                # TODO: ALSO END if previous raw_text for the item is something like k[g]\s*[0-9,]\s*
                print(f"FINISHING ITEM 0: {item}")
                items.append(item)
                item = []

            item.append(raw_item)
            item_text = ' '.join([i[1] for i in item])
            print(f"{item_text=}")

            # End of item info by getting the final price
            if i_name and re.search(r'\d [ABCE]', i_name[-3:]) or re.search(r'[0-9,]+\s*[ABCE]$', item_text):
                if item:
                    print(f"FINISHING ITEM 1: {item}")
                    items.append(item)
                item = []
        return items

    def process_grocery_list(self, items):
        for item_indx, item in enumerate(items):
            raw_text = ' '.join([i[1] for i in item])
            # Make Ks, KG etc. lowercase
            raw_text = re.sub('( k[sg])', lambda pat: pat.group(1).lower(), raw_text, flags=re.I)

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
                if self.shop == 'yeme':
                    final_price = float_sk(re.search(r'\d+,\d+ (\d+,\d{2})', prices).group(1))  # first float is price per kg
                    self.grocery_list.append({'name': i_name, 'amount': amount, 'final_price': final_price})

                if self.shop == 'lidl' or not self.shop:
                    sub_price = get_sub_price(prices)

                    next_item = items[item_indx + 1] if item_indx + 1 < len(items) else []
                    discount = get_discount_from_item(next_item)
                    final_price = round(amount * sub_price - discount, 2)

                    self.grocery_list.append({'name': i_name, 'amount': amount, 'final_price': final_price})

            except Exception as e:
                print(f"Error processing {raw_text} {e}")


if __name__ == '__main__':
    main()
