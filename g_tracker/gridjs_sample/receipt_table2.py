from flask import render_template
from models import Receipt, Person, app, db


def get_receipts_with_person_name(db):
    return db.session.query(
        Receipt, Person
    ).filter(
        Receipt.person_id == Person.person_id
    ).all()


@app.route('/')
def index():
    with app.app_context():
        receipts_persons = get_receipts_with_person_name(db)
        return render_template('receipt_table.html', receipts_persons=receipts_persons)


if __name__ == '__main__':
    app.run()
