from flask import Blueprint, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from sqlalchemy import select, func, insert, delete
from g_tracker.models import Person, Receipt, db
from g_tracker.helpers import *

bp = Blueprint('insight', __name__)


def get_total_spent():
    person_id = int(current_user.get_id())
    spent = db.session.execute(
        select(func.sum(Receipt.total)).where(Receipt.person_id == person_id) \
            .order_by(Receipt.receipt_id.desc())  # Show recently added receipts on top
    ).first()[0]
    return round(spent)

# def get_total_spent(person):
#     sql = 'SELECT SUM(total) FROM receipt WHERE person_id=?'
#     total_spent = db.cur.execute(sql, [person.id]).fetchone()[0]
#     if total_spent is None:
#         raise ValueError(f"{person.name} doesn't have any receipts.")
#
#     sql = ' SELECT MIN(shopping_date), MAX(shopping_date) FROM receipt WHERE person_id = ?'
#     # from_dt, until_dt = [get_local_dt_from_iso(iso_dt) for iso_dt
#     #                      in db.cur.execute(sql, [person.id]).fetchone()]
#     #
#     # time_diff = until_dt - from_dt
#     # when_substr = f"since {from_dt.strftime('%d.%m.%Y')} in {time_diff.days} days"
#     when_substr = ''
#     print(f"\n{person.name} spent a total of {round(total_spent)} {person.currency} on groceries {when_substr}")


@bp.route("/insight", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "POST":
        # return redirect(request.url)
        # return redirect(url_for('item_table.items'))
        pass

    person_id = int(current_user.get_id())
    print(person_id)
    full_filename = f'/static/user_{person_id}/yeme4.jpg'
    print(f"{full_filename=}")

    return render_template("insight.html", spent=get_total_spent(), image=full_filename)