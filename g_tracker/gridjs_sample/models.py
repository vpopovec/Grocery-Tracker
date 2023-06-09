# from sqlalchemy import Column, Integer, Float, String, Date, ForeignKey, UniqueConstraint, Text
# from sqlalchemy.ext.declarative import declarative_base
# from sqlalchemy.orm import relationship
# from sqlalchemy import event
#
# from flask import Flask
# from flask_sqlalchemy import SQLAlchemy
# app = Flask(__name__)
#
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///receipts.db'
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# db = SQLAlchemy(app)
#
# # Base = declarative_base()
#
#
# class Receipt(db.Model):
#     __tablename__ = "receipt"
#     receipt_id = Column(Integer, primary_key=True)
#     person_id = Column(Integer, ForeignKey("person.person_id"), nullable=False)
#     shop_name = Column(Text, index=True)
#     total = Column(Float, nullable=False)
#     shopping_date = Column(Date)
#     person = relationship("Person")
#     # Delete items on deletion of receipt (not on replace, leider)
#     items = relationship("Item", backref="receipt", cascade="all, delete-orphan")
#
#     # ensure unique receipts for 1 person
#     __table_args__ = (
#         UniqueConstraint('person_id', 'shopping_date', name='_person_shopping_date_uc'),
#     )
#
#     def __repr__(self):
#         return f"Receipt {self.receipt_id} from {self.shop_name}, {self.shopping_date}"
#
#
# class Person(db.Model):
#     __tablename__ = "person"
#     person_id = Column(Integer, primary_key=True)
#     phone = Column(String, nullable=False, unique=True)
#     name = Column(String, nullable=False)
#
#     def __repr__(self):
#         return f"Person {self.name}, phone {self.phone}"
#
#
# class Item(db.Model):
#     __tablename__ = "item"
#     item_id = Column(Integer, primary_key=True)
#     price = Column(Float, nullable=False)
#     amount = Column(Float)
#     name = Column(Text, nullable=False)
#     receipt_id = Column(Integer, ForeignKey("receipt.receipt_id"))
#
#     def __repr__(self):
#         return f"Item {self.name} amount {self.amount}, total of {self.price} EUR"
#
#     def to_dict(self):
#         return {
#             'id': self.item_id,
#             'price': self.price,
#             'amount': self.amount,
#             'name': self.name
#         }
#
