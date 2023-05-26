import sqlite3
from datetime import datetime
import pytz
from collections import namedtuple


def get_iso_from_slovak_dt_str(slovak_dt):
    input_format = "%d-%m-%Y %H:%M:%S"
    source_timezone = pytz.timezone("Europe/Bratislava")

    # Parse the input string as a datetime object in the source timezone
    source_datetime = datetime.strptime(slovak_dt, input_format)
    source_datetime = source_timezone.localize(source_datetime)

    # Convert the datetime to UTC
    return source_datetime.astimezone(pytz.utc).isoformat()


def create_connection(db_file):
    """ create a database connection to the SQLite database
        specified by db_file
    :param db_file: database file
    :return: Connection object or None
    """
    try:
        return sqlite3.connect(db_file)
    except sqlite3.Error as e:
        print(e)


def load_db_schema(conn, schema_fp):
    # LOAD SCHEMA
    with open(schema_fp) as fp:
        conn.executescript(fp.read())


def insert_data(conn):
    phone = '123'
    person_task = (phone, 'Test 2')
    sql = ''' INSERT INTO person(phone, name)
                  VALUES(?,?) '''
    cur = conn.cursor()
    try:
        cur.execute(sql, person_task)
        person_id = cur.lastrowid
    except sqlite3.IntegrityError:
        print(f"Person with phone number {phone} is already registered")
        person_id = cur.execute('SELECT person_id FROM person WHERE phone=?', [phone]).fetchone()[0]

    sql = ''' INSERT INTO receipt(person_id, shop_name, total, shopping_date) 
                    VALUES(?,?,?,?) '''
    print(f"QUERIED for {phone} {person_id=}")
    # EXTRACTED DT 29-05-2022 07:57:44
    receipt_task = (person_id, 'lidl', 123.27, get_iso_from_slovak_dt_str("29-05-2022 07:57:44"))
    cur.execute(sql, receipt_task)
    receipt_id = cur.lastrowid
    print(f"INSERTED {receipt_id=}")

    sql = ''' INSERT INTO item(name, price, amount, receipt_id) 
                    VALUES(?,?,?,?) '''
    item_tasks = [('jogurt', 9.95, 5, receipt_id), ('šunka', 1.56, 1.123, receipt_id)]
    for item_task in item_tasks:
        cur.execute(sql, item_task)

    conn.commit()


def insert_groceries(conn, receipt):
    cur = conn.cursor()

    # GET PERSON_ID
    phone = input('Please input last 3 digits of your phone number: ')
    sql = ' SELECT person_id, name FROM person WHERE phone=?'
    person_result = cur.execute(sql, [phone]).fetchone()
    if person_result is None:
        # REGISTER NEW PERSON INTO DB
        name = input("You're new! Please type in your name: ")
        insert_person_sql = " INSERT INTO person(phone, name) VALUES(?,?) "
        cur.execute(insert_person_sql, [phone, name])
        person_id = cur.lastrowid
    else:
        person_id, name = person_result

    print(f'{person_id=}, {name=}')

    # Insert info into receipt table
    sql = ''' INSERT INTO receipt(person_id, shop_name, total, shopping_date) VALUES(?,?,?,?) '''
    receipt_task = (person_id, receipt.shop, receipt.total, get_iso_from_slovak_dt_str(receipt.shopping_date))
    cur.execute(sql, receipt_task)
    receipt_id = cur.lastrowid

    print(f"{receipt.total=} {receipt.shop=} {receipt.shopping_date=}")
    # DELETE orphan items
    cur.execute('DELETE FROM item WHERE receipt_id NOT IN (SELECT receipt_id FROM receipt)')

    sql = ''' INSERT INTO item(name, price, amount, receipt_id) VALUES(?,?,?,?) '''
    # Insert items into DB
    for item in receipt.grocery_list:
        print(item)
        item_task = (item['name'], item['final_price'], item['amount'], receipt_id)
        cur.execute(sql, item_task)

    conn.commit()


def drop_tables(conn):
    cur = conn.cursor()
    for table in ['person', 'receipt', 'item']:
        try:
            cur.execute(f'DROP TABLE {table}')
        except sqlite3.OperationalError:
            pass
    conn.commit()


if __name__ == '__main__':
    grocery_list = [
        {'name': 'Jahod. zmrz_ Crisp', 'amount': 1, 'final_price': 0.89},
        {'name': 'Vajcia "M" 1Oks', 'amount': 1, 'final_price': 2.99},
        {'name': 'Filety z Iososa', 'amount': 1, 'final_price': 6.99},
        {'name': 'Gr.jogurt 0% tuku', 'amount': 6, 'final_price': 2.7},
        {'name': 'syr plát. -sandwich', 'amount': 1, 'final_price': 1.99},
        {'name': 'Strúhaná Gouda', 'amount': 1, 'final_price': 1.79},
        {'name': 'šunka výber_', 'amount': 1, 'final_price': 1.29},
        {'name': 'Termix vani Ika XXL', 'amount': 1, 'final_price': 0.79},
        {'name': 'Tvaroh roztier', 'amount': 1, 'final_price': 1.79},
        {'name': 'Tort. Wraps 6x25cm', 'amount': 1, 'final_price': 1.49},
        {'name': 'Paradajky datl.st', 'amount': 1, 'final_price': 2.19},
        {'name': 'Červ paprika 500g', 'amount': 1, 'final_price': 1.99},
        {'name': 'Hrozien. Thompson', 'amount': 1, 'final_price': 0.99},
        {'name': 'Ženla Fitness', 'amount': 4, 'final_price': 1.0},
        {'name': 'Brusnice sušené', 'amount': 1, 'final_price': 1.99},
        {'name': 'Mal 125g', 'amount': 1, 'final_price': 1.99},
        {'name': 'Banány', 'amount': 0.698, 'final_price': 1.18},
        {'name': 'Hamburgerová žemla', 'amount': 2, 'final_price': 0.98},
        {'name': 'Jablká Fengapi', 'amount': 0.604, 'final_price': 0.9}
    ]
    Receipt_nt = namedtuple('Receipt', ('total', 'shop', 'shopping_date', 'grocery_list'))
    receipt = Receipt_nt(35.92, 'lidl', '25-05-2023 13:08:47', grocery_list)
    print(f'{receipt=}')

    conn = create_connection('receipts.db')
    if conn is not None:
        # drop_tables(conn)
        load_db_schema(conn, 'receipts_schema.sql')
        insert_groceries(conn, receipt)
