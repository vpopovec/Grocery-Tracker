import sqlite3
from datetime import datetime
import pytz


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

    """
    price real NOT NULL,
    amount real,
	receipt_id integer,
	"""

    sql = ''' INSERT INTO item(name, price, amount, receipt_id) 
                    VALUES(?,?,?,?) '''
    item_tasks = [('jogurt', 9.95, 5, receipt_id), ('šunka', 1.56, 1.123, receipt_id)]
    for item_task in item_tasks:
        cur.execute(sql, item_task)

    conn.commit()


if __name__ == '__main__':
    conn = create_connection('receipts.db')
    if conn is not None:
        load_db_schema(conn, 'receipts_schema.sql')
        insert_data(conn)
