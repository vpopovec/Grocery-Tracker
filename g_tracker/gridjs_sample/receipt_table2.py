from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from modules import Receipt, Person, app, db
# app = Flask(__name__)
#
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///receipts.db'
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# db = SQLAlchemy(app)


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
