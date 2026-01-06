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


def float_sk(num_str):
    return float(num_str.replace(',', '.'))


def valid_date_str(dt_str):
    try:
        datetime_object = datetime.strptime(dt_str, '%m-%d-%y %H:%M:%S')
        print(datetime_object)
        return True
    except:
        return False


def fix_amount_int(amount):
    return int(amount.replace('i', '1').replace('{', '1'))


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

