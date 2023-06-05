from flask import render_template
from modules import Receipt, Person, Item, db, app


@app.route('/')
def index():
    with app.app_context():
        # Pass in the f_path (receipt picture)
        # Process the receipt

        # query the Items
        items = Item.query.filter(Item.receipt_id == 2).all()
        return render_template('item_table.html', items=items)


if __name__ == '__main__':
    app.run()
