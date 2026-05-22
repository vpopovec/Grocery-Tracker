from datetime import date, datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from g_tracker import db, login


class Receipt(db.Model):
    __tablename__ = "receipt"
    receipt_id = db.Column(db.Integer, primary_key=True)
    person_id = db.Column(db.Integer, db.ForeignKey("person.person_id"), nullable=False)
    shop_name = db.Column(db.Text, index=True)
    total = db.Column(db.Float, nullable=False)
    shopping_date = db.Column(db.DateTime)
    llm_elapsed_seconds = db.Column(db.Float, nullable=True)
    person = db.relationship("Person", backref="receipt")
    # Delete items on deletion of receipt (not on replace, leider)
    items = db.relationship("Item", backref="receipt", cascade="all, delete-orphan")
    scan = db.relationship("Scan")
    # Todo: Delete picture of receipt on deletion of receipt

    # ensure unique receipts for 1 person
    __table_args__ = (
        db.UniqueConstraint('person_id', 'shop_name', 'shopping_date', 'total', name='_person_shopping_date_uc'),
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


class PasswordResetToken(db.Model):
    __tablename__ = 'password_reset_token'
    id = db.Column(db.Integer, primary_key=True)
    person_id = db.Column(db.Integer, db.ForeignKey('person.person_id'), nullable=False)
    token_hash = db.Column(db.String(64), nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime, nullable=True)

    def is_valid(self) -> bool:
        if self.used_at is not None:
            return False
        return datetime.utcnow() < self.expires_at


@login.user_loader
def load_user(person_id):
    return Person.query.get(int(person_id))


class Item(db.Model):
    __tablename__ = "item"
    item_id = db.Column(db.Integer, primary_key=True)
    price = db.Column(db.Float, nullable=False)
    amount = db.Column(db.Float)
    name = db.Column(db.Text, nullable=False)
    macro_category = db.Column(db.Text, nullable=False, default="Ostatné")
    micro_category = db.Column(db.Text, nullable=False, default="Nezaradené")
    receipt_id = db.Column(db.Integer, db.ForeignKey("receipt.receipt_id"))

    def __repr__(self):
        return f"<Item {self.name} for {self.price} EUR>"

    def to_dict(self):
        return {
            'id': self.item_id,
            'price': self.price,
            'amount': self.amount,
            'name': self.name,
            'macro_category': self.macro_category,
            'micro_category': self.micro_category
        }


class Scan(db.Model):
    __tablename__ = "scan"
    scan_id = db.Column(db.Integer, primary_key=True)
    f_name = db.Column(db.Text, nullable=False, unique=True)
    person_id = db.Column(db.Integer, db.ForeignKey("person.person_id"))
    receipt_id = db.Column(db.Integer, db.ForeignKey("receipt.receipt_id"))

    def __repr__(self):
        return f"<Scan {self.f_name}>"


class LlmDailyUsage(db.Model):
    """Tracks paid LLM calls per user per day (receipt scans, insight chat, …)."""

    __tablename__ = 'llm_daily_usage'
    id = db.Column(db.Integer, primary_key=True)
    person_id = db.Column(db.Integer, db.ForeignKey('person.person_id'), nullable=False)
    usage_date = db.Column(db.Date, nullable=False)
    usage_kind = db.Column(db.String(32), nullable=False)
    usage_count = db.Column(db.Integer, nullable=False, default=0)

    __table_args__ = (
        db.UniqueConstraint(
            'person_id', 'usage_date', 'usage_kind', name='_person_usage_kind_date_uc'),
    )
