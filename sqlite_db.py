import os.path
import sqlite3
from helpers import get_datetime_from_slovak_dt
db_fp = 'receipts.db'
schema_fp = 'receipts_schema.sql'


def load_db_schema(conn, schema_fp):
    with open(schema_fp) as fp:
        conn.executescript(fp.read())


def ensure_receipt_llm_elapsed_column(conn):
    """Add llm_elapsed_seconds to legacy databases that predate this column."""
    info = conn.execute("PRAGMA table_info(receipt)").fetchall()
    names = {row[1] for row in info}
    if "llm_elapsed_seconds" not in names:
        conn.execute("ALTER TABLE receipt ADD COLUMN llm_elapsed_seconds REAL")
        conn.commit()


def ensure_llm_daily_usage_schema(conn):
    """Migrate llm_daily_usage from legacy scan_count schema to usage_count + usage_kind."""
    if not conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='llm_daily_usage'"
    ).fetchone():
        return

    names = {row[1] for row in conn.execute("PRAGMA table_info(llm_daily_usage)").fetchall()}
    if "usage_count" in names and "usage_kind" in names:
        return

    if "scan_count" in names:
        conn.executescript(
            """
            CREATE TABLE llm_daily_usage_new (
                id INTEGER NOT NULL PRIMARY KEY,
                person_id INTEGER NOT NULL,
                usage_date DATE NOT NULL,
                usage_kind VARCHAR(32) NOT NULL,
                usage_count INTEGER NOT NULL,
                CONSTRAINT _person_usage_kind_date_uc
                    UNIQUE (person_id, usage_date, usage_kind),
                FOREIGN KEY(person_id) REFERENCES person (person_id)
            );
            INSERT INTO llm_daily_usage_new
                (id, person_id, usage_date, usage_kind, usage_count)
            SELECT id, person_id, usage_date, 'receipt_scan', scan_count
            FROM llm_daily_usage;
            DROP TABLE llm_daily_usage;
            ALTER TABLE llm_daily_usage_new RENAME TO llm_daily_usage;
            """
        )
        conn.commit()
        return

    if "usage_count" in names and "usage_kind" not in names:
        conn.execute(
            "ALTER TABLE llm_daily_usage "
            "ADD COLUMN usage_kind VARCHAR(32) NOT NULL DEFAULT 'receipt_scan'"
        )
        conn.commit()


class Database:
    # Disable same check thread to allow usage across multiple requests
    conn = sqlite3.connect(db_fp, check_same_thread=False)
    load_db_schema(conn, schema_fp)
    ensure_receipt_llm_elapsed_column(conn)

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
        sql = ''' INSERT INTO receipt(person_id, shop_name, total, shopping_date, llm_elapsed_seconds) VALUES(?,?,?,?,?) '''
        date_iso = receipt.shopping_date
        llm_s = getattr(receipt, "llm_elapsed_seconds", None)
        receipt_task = (person_id, receipt.shop, receipt.total, date_iso, llm_s)
        self.cur.execute(sql, receipt_task)
        receipt_id = self.cur.lastrowid

        # DELETE orphan items
        self.cur.execute('DELETE FROM item WHERE receipt_id NOT IN (SELECT receipt_id FROM receipt)')

        sql = ''' INSERT INTO item(name, price, amount, macro_category, micro_category, receipt_id) VALUES(?,?,?,?,?,?) '''
        # Insert items into DB
        for item in receipt.grocery_list:
            print(item)
            item_task = (item['name'], item['final_price'], item['amount'], item['macro_category'], item['micro_category'], receipt_id)
            self.cur.execute(sql, item_task)

        sql = ''' INSERT INTO scan(f_name, person_id, receipt_id) VALUES(?,?,?) '''
        f_name = f_name or os.path.basename(receipt.f_name)
        self.cur.execute(sql, (f_name, person_id, receipt_id))

        Database.conn.commit()
        return receipt_id
