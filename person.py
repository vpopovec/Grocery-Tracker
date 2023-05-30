from db import Database
from helpers import get_phone_input


class Person:
    db = Database()

    def __init__(self, phone: str = ''):
        self.phone = phone or get_phone_input()
        self.id, self.name = Person.db.get_person_id_name(self.phone)
        self.currency = 'EUR'
