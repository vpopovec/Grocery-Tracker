import os.path
import sqlite3
from helpers import get_datetime_from_slovak_dt
db_fp = 'receipts.db'
schema_fp = 'receipts_schema.sql'


def load_db_schema(conn, schema_fp):
    with open(schema_fp) as fp:
        conn.executescript(fp.read())


class Database:
    # Disable same check thread to allow usage across multiple requests
    conn = sqlite3.connect(db_fp, check_same_thread=False)
    load_db_schema(conn, schema_fp)

    def __init__(self):
        # Unique cursor for every Database instance
        self.cur = Database.conn.cursor()

    def get_person_id_name(self, email: str):
        # Get person by email
        sql = ' SELECT person_id, name FROM person WHERE email=? '
        person_result = self.cur.execute(sql, [email]).fetchone()

        if person_result is None:
            # REGISTER NEW PERSON
            username = input("You're new! Please type in your username: ")
            name = input("You're new! Please type in your nickname: ")
            insert_person_sql = " INSERT INTO person(email, username, name) VALUES(?,?,?) "
            self.cur.execute(insert_person_sql, [email, username, name])
            Database.conn.commit()

            person_id = self.cur.lastrowid
        else:
            person_id, name = person_result
            print(f'Welcome back, {name}!')

        return person_id, name

    def save_receipt(self, receipt, person_id, f_name='') -> int:
        if not receipt.total or not receipt.grocery_list:
            raise ValueError(f'Receipt is empty {receipt.total} len {len(receipt.grocery_list)}')

        # Insert info into receipt table
        sql = ''' INSERT INTO receipt(person_id, shop_name, total, shopping_date) VALUES(?,?,?,?) '''
        date_iso = receipt.shopping_date
        receipt_task = (person_id, receipt.shop, receipt.total, date_iso)
        self.cur.execute(sql, receipt_task)
        receipt_id = self.cur.lastrowid

        # DELETE orphan items
        self.cur.execute('DELETE FROM item WHERE receipt_id NOT IN (SELECT receipt_id FROM receipt)')

        sql = ''' INSERT INTO item(name, price, amount, receipt_id) VALUES(?,?,?,?) '''
        # Insert items into DB
        for item in receipt.grocery_list:
            print(item)
            item_task = (item['name'], item['final_price'], item['amount'], receipt_id)
            self.cur.execute(sql, item_task)

        sql = ''' INSERT INTO scan(f_name, person_id, receipt_id) VALUES(?,?,?) '''
        f_name = f_name or os.path.basename(receipt.f_name)
        self.cur.execute(sql, (f_name, person_id, receipt_id))

        Database.conn.commit()
        return receipt_id
