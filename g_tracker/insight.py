from flask import Blueprint, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from sqlalchemy import select, func, insert, delete
from g_tracker.models import Person, Receipt, Item, db
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

    monthly_sum = df.resample('ME').sum()
    monthly_sum = monthly_sum.reset_index()
    # Remove months with no activity
    # monthly_sum = monthly_sum[monthly_sum['total'] > 0].reset_index()
    print(f"Date Range: {df.index.min()} to {df.index.max()}")

    chart = alt.Chart(monthly_sum).mark_bar().encode(
        x=alt.X('date:O', 
                timeUnit='yearmonth', 
                title='Timeline',
                axis=alt.Axis(labelAngle=-45, format='%b %Y')), 
        y=alt.Y('total:Q', title='Total Spending')
    )
    chart.save(f'{static_path}monthly_spending.png')

    # --- Category Breakdown Logic ---
    # Query all items belonging to this user's receipts
    category_data = db.session.query(
        Item.macro_category,
        func.sum(Item.price).label('total_price')
    ).join(Receipt, Item.receipt_id == Receipt.receipt_id) \
     .filter(Receipt.person_id == person_id) \
     .group_by(Item.macro_category).all()

    # Convert to DataFrame
    cat_df = pd.DataFrame(category_data, columns=['category', 'total'])

    # Create Donut Chart
    category_chart = alt.Chart(cat_df).mark_arc(innerRadius=50).encode(
        theta=alt.Theta(field="total", type="quantitative"),
        color=alt.Color(field="category", type="nominal", title="Category"),
        tooltip=['category', 'total']
    ).properties(
        title="Spending by Category",
        width=300,
        height=300
    )

    category_chart.save(f'{static_path}category_breakdown.png')


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
    macro_category_fn = f"static/graphs/{person_id}/category_breakdown.png"

    return render_template("insight.html", spent=get_total_spent(), weekly=weekly_fn, monthly=monthly_fn, macro_category=macro_category_fn)
