from flask import render_template, request, abort, current_app, Blueprint
from sqlalchemy import select
from g_tracker.models import Person, Receipt, Item, db
# TODO: Try moving models imports here

bp = Blueprint('item_table', __name__)


def get_receipts_with_person_name():
    return db.session.query(
        Receipt, Person
    ).filter(
        Receipt.person_id == Person.person_id
    ).all()


@bp.route('/receipts')
def receipts():
    with current_app.app_context():
        receipts_persons = get_receipts_with_person_name()
        return render_template('receipt_table.html', receipts_persons=receipts_persons)


@bp.route('/items')
def items():
    """
    Displays editable table of items for the last receipt
    :return:
    """
    receipt_id = request.args.get('receipt_id')
    if receipt_id:
        print(f"TYPE OF RECEIVED RECEIPT ID AS PARAMETER {type(receipt_id)} {receipt_id}")
        current_app.config['RECEIPT_ID'] = int(receipt_id)
    with current_app.app_context():
        receipt_f_name = ''
        return render_template('item_table.html', receipt_f_name=receipt_f_name)


@bp.route('/api/data')
def data():
    try:
        # TODO: Use g instead of config?
        current_receipt_id = current_app.config['RECEIPT_ID']
    except KeyError:
        current_receipt_id = 2
    query = Item.query.filter(Item.receipt_id == current_receipt_id)

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


@bp.route('/api/data', methods=['POST'])
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
