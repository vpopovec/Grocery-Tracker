from modules import Receipt, Person, db, app

with app.app_context():
    db.create_all()
    # receipts = Receipt.query.all()
    receipts = db.session.query(
        Receipt, Person
    ).filter(
        Receipt.person_id == Person.person_id
    ).all()
    for r, p in receipts:
        print(r)
        print(p.name)
