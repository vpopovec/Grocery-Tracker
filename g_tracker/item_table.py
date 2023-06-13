from flask import render_template, request, abort, current_app, Blueprint, send_file, url_for, redirect
from flask_login import login_required, current_user
from sqlalchemy import select, func, insert, delete
from g_tracker.models import Person, Receipt, Item, Scan, db
import os

bp = Blueprint('item_table', __name__)


def get_receipts_with_person_name():
    person_id = int(current_user.get_id())
    return db.session.query(
        Receipt, Person
    ).filter(
        Receipt.person_id == person_id
    ).all()


@bp.route('/receipts')
@login_required
def receipts():
    with current_app.app_context():
        receipts_persons = get_receipts_with_person_name()
        return render_template('receipt_table.html', receipts_persons=receipts_persons)


@bp.route('/add-row')
@login_required
def add_row():
    # Note: Page must be reloaded to reflect changes
    db.session.execute(insert(Item).values(
        price=0.0,
        amount=1,
        name="item",
        receipt_id=current_app.config['RECEIPT_ID']
    ))
    db.session.commit()
    return redirect(url_for('item_table.items'))


@bp.route('/delete-row')
@login_required
def delete_row():
    item_id = int(request.args.get('item_id'))
    db.session.execute(delete(Item).where(Item.item_id == item_id))

    update_receipt_total()
    db.session.commit()

    return redirect(url_for('item_table.items'))


def update_receipt_total():
    # Change receipt's total to reflect changes
    current_receipt_id = current_app.config.get('RECEIPT_ID', 1)

    receipt_total = round(db.session.query(
        func.sum(Item.price)).join(Receipt) \
        .filter(Receipt.receipt_id == current_receipt_id).scalar(), 2)

    receipt = db.session.execute(select(Receipt).where(Receipt.receipt_id == current_receipt_id)).first()[0]
    setattr(receipt, 'total', receipt_total)


@bp.route('/items')
@login_required
def items():
    """
    Displays editable table of items for the last receipt
    :return:
    """
    receipt_id = request.args.get('receipt_id')
    if receipt_id:
        current_app.config['RECEIPT_ID'] = int(receipt_id)
    with current_app.app_context():
        return render_template('item_table.html')


@bp.route('/api/data')
@login_required
def data():
    current_receipt_id = current_app.config.get('RECEIPT_ID', 1)

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
@login_required
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

    # Changing Item's price
    if 'price' in data:
        update_receipt_total()

    db.session.commit()
    return '', 204


@bp.route('/photo')
@login_required
def photo():
    # TODO: Only allow user to see his own photos
    if f_name := request.args.get('f_name'):
        f_path = os.path.join(current_app.config['UPLOAD_FOLDER'], f_name)
        return send_file(f_path)

    # Get photo for current receipt
    current_receipt_id = current_app.config.get('RECEIPT_ID', 1)
    scan = db.session.execute(select(Scan).where(Scan.receipt_id == current_receipt_id)).first()[0]
    print('scan', scan)
    return redirect(url_for('item_table.photo', f_name=scan.f_name))
