from flask import Blueprint, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from sqlalchemy import select, func, insert, delete
from g_tracker.models import Person, Receipt, db
from g_tracker.helpers import *
from g_tracker.item_table import get_receipts
import altair as alt
import pandas as pd
from pathlib import Path

bp = Blueprint('insight', __name__)
# to_utc = lambda dt: dt.replace(' ', 'T') + "Z"


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


def create_graphs():
    person_id = int(current_user.get_id())
    receipts = get_receipts()

    df_cols = {"total": [], "date": []}
    for receipt, buyer in receipts:
        df_cols['total'].append(receipt.total)
        df_cols['date'].append(receipt.shopping_date)

    df = pd.DataFrame.from_dict(df_cols)
    df['date'] = pd.to_datetime(df['date'])
    print(df.info())
    df.set_index('date', inplace=True)
    # weekly_sum = df.resample('M').sum()
    weekly_sum = df.resample('W-Mon').sum()
    weekly_sum = weekly_sum.reset_index()

    chart = alt.Chart(weekly_sum).mark_bar().encode(
        x='date',
        y='total',
    )
    static_path = f"g_tracker/static/graphs/{person_id}/"
    Path(static_path).mkdir(parents=True, exist_ok=True)

    chart.save(f'{static_path}weekly_spending.png')

    monthly_sum = df.resample('M').sum()
    monthly_sum = monthly_sum.reset_index()

    chart = alt.Chart(monthly_sum).mark_bar().encode(
        x='date',
        y='total',
    )
    chart.save(f'{static_path}monthly_spending.png')


@bp.route("/insight", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "POST":
        # return redirect(request.url)
        # return redirect(url_for('item_table.items'))
        pass

    create_graphs()
    person_id = int(current_user.get_id())
    weekly_fn = f"static/graphs/{person_id}/weekly_spending.png"
    monthly_fn = f"static/graphs/{person_id}/monthly_spending.png"

    return render_template("insight.html", spent=get_total_spent(), weekly=weekly_fn, monthly=monthly_fn)
