from sqlalchemy import Column, Integer, Float, String, Date, ForeignKey
from sqlalchemy.ext.declarative import declarative_base

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///receipts.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Base = declarative_base()


class Receipt(db.Model):
    __tablename__ = "receipt"
    receipt_id = Column(Integer, primary_key=True)
    person_id = Column(Integer, ForeignKey("person.person_id"), nullable=False)
    shop_name = Column(String(64), index=True)
    total = Column(Float, nullable=False)
    shopping_date = Column(Date)

    def __repr__(self):
        return f"Receipt {self.receipt_id} from {self.shop_name}, {self.shopping_date}"


class Person(db.Model):
    __tablename__ = "person"
    person_id = Column(Integer, primary_key=True)
    phone = Column(String(20), nullable=False, unique=True)
    name = Column(String(200), nullable=False)

    def __repr__(self):
        return f"Person {self.name}, phone {self.phone}"
