import json
import os
import re
import traceback
import numpy as np
import pytz
from datetime import datetime
from unidecode import unidecode
from g_tracker.helpers import ROOT_DIR
MINUS_SIGN = '[-~]'
NUMBER = r'\d+[.,]\s*\d{2}'
CACHE_PATH = os.path.join(ROOT_DIR, 'receipts', 'cache')
d_r = r'[0-3]\d'
m_r = r'[01]\d'
y_r = r'2\d\d\d'


# def get_item_name(item_name):
#     item_alphas = len([c for c in item_name if c.isalpha() and c not in ['B', 'E']])
#     # don't count pcs (pieces) as item name
#     if 'ks' in item_name[:3] or ' ks' in item_name:
#         item_alphas -= 2
#     # don't count weight units as item name
#     if 'kg' in item_name:
#         item_alphas -= 2
#     if item_alphas > 1:
#         return item_name


# def fix_item_name(name):
#     name = ' '.join(name.split())
#     name = f"{name[:-1]}g" if name[-1] == '9' else name

#     typos = [(' .', '.'), (' ,', '.'), (' ml', ' ml'), (' m1', ' ml'), (' m}', ' ml')]
#     for typo in typos:
#         name = name.replace(typo[0], typo[1])

#     # Extra manual fixes
#     name = name.replace('najmeng', 'najmens')
#     name = re.sub(r'.apusta', 'kapusta', name)

#     name = re.sub(r'( \d+)\*', lambda pat: f"{pat.group(1)}%", name)
#     name = re.sub(r'( \d+[94])', lambda pat: f"{pat.group(1)[:-1]}g", name)  # g sometimes read as 9 or 4
#     return name.capitalize()


# def get_sub_price(price, is_pcs=None, amount=0):
#     print(f"EXTRACTING SUBPRICE FROM {price=}")
#     if is_pcs:
#         # Second number (final_price) is optional, only present in multiple pcs
#         if amount >= 1:
#             final_price_gr = re.search(r'(\d+)\D(\d{2}).?.?$', price)
#             if final_price_gr:
#                 final_price = int(final_price_gr.group(1)) + int(final_price_gr.group(2)) / 100
#                 return round(final_price / amount, 2)

#         prices = re.search(r'(\d+)\D+(\d{2})(\s+\d+\D+\d{2})?', price)
#         if prices is not None:
#             # Return the price of 1 pc
#             return int(prices.group(1)) + int(prices.group(2)) / 100

#         # Missing a digit
#         if cents := re.search(r'\d{2}', price):
#             # Assume it was .cents
#             return round(int(cents.group(0)) / 100, 2)

#     elif not is_pcs:
#         prices = re.search(r'(\d+)\D+(\d{2})\D+(\d+)\D+(\d{2})', price)
#         if prices:
#             return int(prices.group(1)) + int(prices.group(2)) / 100

#     if price_amount := re.search(r'\d+,\d+', price):
#         # Not really sure about this one... For kgs?
#         return round(float_sk(price_amount.group(0)), 2)

#     if price_str := re.search(r'[^,.]+(\d+)\s+[.,]?(\d{2})\s*[BCE]', price):
#         # Return the price of all pcs (final_price)
#         return int(price_str.group(1)) + int(price_str.group(2)) / 100

#     if price_str := re.search(r'(\d+)\s+[.,]?(\d{2})\s*', price):
#         return int(price_str.group(1)) + int(price_str.group(2)) / 100

#     if cents := re.search(r'\d{2}', price):
#         # Assume it was .cents
#         return round(int(cents.group(0)) / 100, 2)


# def is_discount(raw_text):
#     raw_text = unidecode(raw_text.lower().replace(' "', ' -').replace(' ~', ' -'))
#     if re.search(r'z.ava', raw_text, re.I):
#         return True
#     if re.search(r'-\d', raw_text) and re.search(r'zaloh.?a', raw_text, re.I):
#         return True
#     if re.search(r'-\d', raw_text) and 'sucet' not in raw_text and 'uhradu' not in raw_text:  # end of items
#         return True


# def get_discount_from_item(item):
#     # TODO: Replace CHANGING "8 to -0 with a fix
#     try:
#         # raw_text = ' '.join([i[1] for i in item]).lower().replace(' "8', ' -0').replace(' "', ' -').replace(' ~', ' -')
#         # raw_text = unidecode(raw_text)

#         # Note: 'zaloha' should not be deducted from the item's price in the future
#         raw_text = ' '.join([i[1] for i in item]).lower().replace(' "8', ' -0')
#         raw_text = re.sub(r' "(\d)', lambda pat: f" -{pat.group(1)}", raw_text)
#         raw_text = re.sub(r'zlava . kup', 'zlava s kup', raw_text, re.I)  # zlava s kuponom, kaufland
#         if not is_discount(raw_text):
#             return 0
#         # if not re.search(r'z.ava', raw_text) and not re.search(r'zaloh.?a', raw_text) and '-' not in raw_text:
#         #     return 0
#         try:
#             amount = int(re.search(r' (\d+) ', raw_text).group(1))
#         except:
#             print(f"CAN'T GET AMOUNT FROM {raw_text} defaulting to 1")
#             amount = 1
#         try:
#             discount_price = re.search(rf'{MINUS_SIGN}({NUMBER})', raw_text).group(1)
#         except AttributeError:  # no minus sign
#             try:
#                 discount_price = re.search(f'({NUMBER})', raw_text).group(1)
#             except AttributeError:
#                 prices = re.search(r'(\d+)\D+(\d{2})', raw_text)
#                 discount_price = f'{prices.group(1)}.{prices.group(2)}'

#         discount_price = round(float_sk(''.join(discount_price.split())), 2)
#         print(f"GOT DISCOUNT FROM {raw_text} {amount=} {discount_price=}")
#         return round(amount * discount_price, 2)
#     except Exception as e:
#         print(f"MAY HAVE SKIPPED A DISCOUNT: {' '.join([i[1] for i in item])}, e={e}")
#         return 0


# def get_shop(receipt):
#     shops = {
#         'yeme': ('yeme', '2024133650', '47793155'),
#         'kaufland': ('kaufland', '2020234216', '35790164'),
#         'lidl': ('lidl', 'lsdl', '2020279415', '35793783'),
#         'billa': ('billa', '2020312503', '31347037'),
#         'tesco': ('tesco', '2020301140', '31321828'),
#         'dm': {'dm ', '2020354534', '31393781'}}
#     receipt_shop = ''
#     for shop, shop_aliases in shops.items():
#         for shop_alias in shop_aliases:
#             receipt_shop = shop if shop_alias in receipt else receipt_shop
#             if receipt_shop:
#                 break
#         if receipt_shop:
#             break

#     # Try regex as well (experimental)
#     receipt_shop = 'lidl' if re.search(r'lid[}]', receipt) else receipt_shop
#     return receipt_shop


def float_sk(num_str):
    return float(num_str.replace(',', '.'))


def valid_date_str(dt_str):
    try:
        datetime_object = datetime.strptime(dt_str, '%m-%d-%y %H:%M:%S')
        print(datetime_object)
        return True
    except:
        return False


# def get_shopping_date(receipt):
#     receipt = receipt.replace('ô', '6').replace('/2', '0')  # temp fix
#     if dt := re.search(rf'({d_r})-({m_r})-({y_r})\s*(\d\d)[.,:;](\d\d)[.,:;](\d\d)', receipt):
#         hour, minute, second = dt.group(4), dt.group(5), dt.group(6)
#     elif dt := re.search(rf'({d_r})-({m_r})-({y_r})\s*(\d\d)\D+(\d\d)\D+(\d\d)', receipt):
#         hour, minute, second = dt.group(4), dt.group(5), dt.group(6)
#     elif dt := re.search(rf'({d_r})-({m_r})-({y_r})\s*(\d\d)[.,:;]..[.,:;]..', receipt):
#         hour, minute, second = dt.group(4), '00', '00'
#     elif dt := re.search(rf'({d_r})\D?({m_r})\D?({y_r})\s*(\d\d)[.,:;](\d\d)[.,:;](\d\d)', receipt):
#         hour, minute, second = dt.group(4), dt.group(5), dt.group(6)
#     elif dt := re.search(rf'({d_r})\D?({m_r})\D?({y_r})\s*(\d\d)', receipt):
#         hour, minute, second = dt.group(4), '00', '00'
#     elif dt := re.search(rf'({d_r})-({m_r})-({y_r})\s*..?.?[.,:;]..', receipt):
#         hour, minute, second = '12', '00', '00'  # Placeholder time
#     elif dt := re.search(rf'({d_r})\D?({m_r})\D?({y_r})', receipt):
#         hour, minute, second = '12', '00', '00'  # Placeholder time

#     if dt:
#         day, month, year = dt.group(1), dt.group(2), dt.group(3)
#         dt_str = f"{'-'.join([day, month, year])} {':'.join([hour, minute, second])}"

#     try:
#         if get_iso_from_slovak_dt_str(dt_str):
#             return dt_str
#     except (ValueError, NameError):
#         return datetime.today().strftime("%d-%m-%Y %H:%M:%S")


def fix_amount_int(amount):
    return int(amount.replace('i', '1').replace('{', '1'))


# def get_iso_from_slovak_dt_str(slovak_dt):
#     input_format = "%d-%m-%Y %H:%M:%S"
#     source_timezone = pytz.timezone("Europe/Bratislava")

#     # Parse the input string as a datetime object in the source timezone
#     source_datetime = datetime.strptime(slovak_dt, input_format)
#     source_datetime = source_timezone.localize(source_datetime)

#     # Convert the datetime to UTC
#     return source_datetime.astimezone(pytz.utc).isoformat()


def get_email_input():
    while True:
        email = input("Please input your email: ")
        # TODO: Validate email
        if '@' in email:
            return email
        print('Invalid email format')


def get_local_dt_from_iso(iso_dt):
    target_tz = pytz.timezone("Europe/Bratislava")

    # Parse ISO to UTC
    utc_datetime = datetime.fromisoformat(iso_dt)

    # Convert the datetime to the target timezone
    return utc_datetime.astimezone(target_tz)


def get_local_dt_formatted_from_iso(iso_dt, dt_format: str = ''):
    slovak_format = '%d.%m.%Y'
    dt_format = dt_format or slovak_format
    return get_local_dt_from_iso(iso_dt).strftime(dt_format)


def get_date_from_slovak_dt(shopping_date: str) -> str:
    return '-'.join(shopping_date.split()[0].split('-')[::-1])


def get_datetime_from_slovak_dt(shopping_date: str) -> str:
    time_ = shopping_date.split()[1]
    return f"{get_date_from_slovak_dt(shopping_date)} {time_}"


def get_cached_receipt(f_name):
    try:
        f_name = os.path.basename(f_name).replace(".", "_") + '.json'
        with open(os.path.join(CACHE_PATH, f_name), encoding='utf8') as rf:
            return json.load(rf)
    except (FileNotFoundError, json.decoder.JSONDecodeError):
        return None


class NpEncoder(json.JSONEncoder):
    # Custom encoder for storing OCR result
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NpEncoder, self).default(obj)


def cache_receipt(receipt, f_name, recursion=0):
    # Cache result of OCR for faster loading (development/testing)
    try:
        print(f"CALLING CACHE_RECEIPT: {recursion=}")
        f_name = os.path.basename(f_name).replace(".", "_") + '.json'
        with open(os.path.join(CACHE_PATH, f_name), 'w', encoding='utf8') as wf:
            # dumps is quicker than dump
            wf.write(json.dumps(receipt, cls=NpEncoder))
    except FileNotFoundError:
        os.mkdir(CACHE_PATH)
        # Avoid infinite loop when more dirs need to be created
        if recursion < 3:
            cache_receipt(receipt, f_name, recursion+1)

