# from flask import Flask, render_template
# from flask_sqlalchemy import SQLAlchemy
# app = Flask(__name__)
#
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///receipts.db'
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# db = SQLAlchemy(app)
#
#
# class Receipt(db.Model):
#     """
#     CREATE TABLE IF NOT EXISTS receipt (
#         receipt_id integer PRIMARY KEY,
#         person_id integer NOT NULL,
#         shop_name text,
#         total real NOT NULL,
#         shopping_date date,
#         FOREIGN KEY (person_id) REFERENCES person (person_id)
#         UNIQUE(person_id, shopping_date) ON CONFLICT REPLACE  -- ensure unique receipts for 1 person
#     );
#     """
#     __tablename__ = 'receipt'
#     receipt_id = db.Column(db.Integer, primary_key=True)
#     person_id = db.Column(db.Integer, nullable=False)
#     shop_name = db.Column(db.String(64), index=True)
#     total = db.Column(db.Float, nullable=False)
#     shopping_date = db.Column(db.Date)
#
#     def __repr__(self):
#         return f"Receipt {self.receipt_id} from {self.shop_name}, {self.shopping_date}"
#
#
# with app.app_context():
#     db.create_all()
#
#
# @app.route('/')
# def index():
#     with app.app_context():
#         receipts = Receipt.query
#         return render_template('receipt_table.html', receipts=receipts)
#
#
# if __name__ == '__main__':
#     app.run()
