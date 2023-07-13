from g_tracker import db, login
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash


class Receipt(db.Model):
    __tablename__ = "receipt"
    receipt_id = db.Column(db.Integer, primary_key=True)
    person_id = db.Column(db.Integer, db.ForeignKey("person.person_id"), nullable=False)
    shop_name = db.Column(db.Text, index=True)
    total = db.Column(db.Float, nullable=False)
    shopping_date = db.Column(db.DateTime)
    person = db.relationship("Person", backref="receipt")
    # Delete items on deletion of receipt (not on replace, leider)
    items = db.relationship("Item", backref="receipt", cascade="all, delete-orphan")
    scan = db.relationship("Scan")
    # Todo: Delete picture of receipt on deletion of receipt

    # ensure unique receipts for 1 person
    __table_args__ = (
        db.UniqueConstraint('person_id', 'shopping_date', name='_person_shopping_date_uc'),
    )

    def __repr__(self):
        return f"<Receipt {self.receipt_id} from {self.shop_name}, {self.shopping_date}>"


class Person(UserMixin, db.Model):
    __tablename__ = "person"
    person_id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String, nullable=False, unique=True)
    username = db.Column(db.String, nullable=False)
    name = db.Column(db.String, nullable=False)
    password_hash = db.Column(db.String(120))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return self.person_id

    def __repr__(self):
        return f"<Person {self.username}, nickname {self.name}>"


@login.user_loader
def load_user(person_id):
    return Person.query.get(int(person_id))


class Item(db.Model):
    __tablename__ = "item"
    item_id = db.Column(db.Integer, primary_key=True)
    price = db.Column(db.Float, nullable=False)
    amount = db.Column(db.Float)
    name = db.Column(db.Text, nullable=False)
    receipt_id = db.Column(db.Integer, db.ForeignKey("receipt.receipt_id"))

    def __repr__(self):
        return f"<Item {self.name} for {self.price} EUR>"

    def to_dict(self):
        return {
            'id': self.item_id,
            'price': self.price,
            'amount': self.amount,
            'name': self.name
        }


class Scan(db.Model):
    __tablename__ = "scan"
    scan_id = db.Column(db.Integer, primary_key=True)
    f_name = db.Column(db.Text, nullable=False, unique=True)
    person_id = db.Column(db.Integer, db.ForeignKey("person.person_id"))
    receipt_id = db.Column(db.Integer, db.ForeignKey("receipt.receipt_id"))

    def __repr__(self):
        return f"<Scan {self.f_name}>"
