from person import Person
from sqlite_db import Database
from helpers import *

db = Database()


def main():
    # phone = '111'
    person = Person()
    get_all_receipts(person)
    get_total_spent(person)


def get_all_receipts(person):
    sql = ' SELECT shop_name, total, shopping_date FROM receipt WHERE person_id=? ORDER BY shopping_date '
    receipts = db.cur.execute(sql, [person.id])
    print(f"\n{person.name}'s receipts:")
    for r_num, receipt in enumerate(receipts, 1):
        shop, total, shopping_date = receipt
        shopping_date = get_local_dt_formatted_from_iso(shopping_date)
        print(f'Receipt #{r_num}: \n\t{shop.capitalize()}, {total} {person.currency}, {shopping_date}')


def get_total_spent(person):
    sql = 'SELECT SUM(total) FROM receipt WHERE person_id=?'
    total_spent = db.cur.execute(sql, [person.id]).fetchone()[0]
    if total_spent is None:
        raise ValueError(f"{person.name} doesn't have any receipts.")

    sql = ' SELECT MIN(shopping_date), MAX(shopping_date) FROM receipt WHERE person_id = ?'
    from_dt, until_dt = [get_local_dt_from_iso(iso_dt) for iso_dt
                         in db.cur.execute(sql, [person.id]).fetchone()]

    time_diff = until_dt - from_dt
    when_substr = f"since {from_dt.strftime('%d.%m.%Y')} in {time_diff.days} days"
    print(f"\n{person.name} spent a total of {round(total_spent)} {person.currency} on groceries {when_substr}")


if __name__ == '__main__':
    main()
