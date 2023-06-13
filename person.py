from sqlite_db import Database
from helpers import get_email_input


class Person:
    db = Database()

    def __init__(self, email: str = '', person_id: int = 0):
        if not person_id:
            self.email = email or get_email_input()
            self.id, self.name = Person.db.get_person_id_name(self.email)
            self.currency = 'EUR'
        else:
            self.id = person_id
