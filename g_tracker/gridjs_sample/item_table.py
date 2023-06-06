from flask import render_template, request, abort
from modules import Receipt, Person, Item, db, app
from sqlalchemy import select


@app.route('/')
def index():
    with app.app_context():
        # Pass in the f_path (receipt picture)
        # Process the receipt

        # query the Items
        # items = Item.query.filter(Item.receipt_id == 2).all()
        return render_template('item_table.html')


@app.route('/api/data')
def data():
    # query = Item.query
    query = Item.query.filter(Item.receipt_id == 2)

    # search filter
    search = request.args.get('search')
    if search:
        query = query.filter(db.or_(
            Item.name.like(f'%{search}%')
        ))
    total = query.count()

    # sorting
    sort = request.args.get('sort')
    if sort:
        order = []
        for s in sort.split(','):
            direction = s[0]
            name = s[1:]
            if name not in ['name', 'total']:
                name = 'name'
            col = getattr(Item, name)
            if direction == '-':
                col = col.desc()
            order.append(col)
        if order:
            query = query.order_by(*order)

    # pagination
    start = request.args.get('start', type=int, default=-1)
    length = request.args.get('length', type=int, default=-1)
    if start != -1 and length != -1:
        query = query.offset(start).limit(length)

    # response
    return {
        'data': [item.to_dict() for item in query],
        'total': total,
    }


@app.route('/api/data', methods=['POST'])
def update():
    data = request.get_json()
    if 'id' not in data:
        print(f"ID NOT IN DATA! CHECK >> {data=}")
        abort(400)

    # Get item by item_id
    item = db.session.execute(select(Item).where(Item.item_id == data['id'])).first()[0]
    for field in ['name', 'amount', 'total', 'price']:
        if field in data:
            setattr(item, field, data[field])
    db.session.commit()
    return '', 204


if __name__ == '__main__':
    app.run()
