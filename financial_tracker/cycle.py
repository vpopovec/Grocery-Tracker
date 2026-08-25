"""Budget cycle boundaries, shared by the dashboard and the transaction browser.

This used to live in streamlit_app.py, but that module runs the whole dashboard UI
at import time, so any other page that wanted the cycle had to re-derive it. Both
copies drifting apart is exactly how a filter stops lining up with the bar it was
supposed to explain.
"""
from datetime import date, datetime

from dateutil.relativedelta import relativedelta

from schema import get_db_connection


def calculate_active_cycle(anchor_day=10):
    """Start and end dates of the cycle containing today, for a given anchor day."""
    today = date.today()
    # Before the anchor day, we are still inside the cycle that opened last month.
    if today.day < anchor_day:
        start_date = today - relativedelta(months=1)
        start_date = start_date.replace(day=anchor_day)
    else:
        start_date = today.replace(day=anchor_day)
    end_date = start_date + relativedelta(months=1) - relativedelta(days=1)
    return start_date, end_date


def get_current_cycle_start(person_id):
    """
    Returns the start date of the active budget cycle. Uses paycheck_metadata when
    it applies to the current cycle; otherwise falls back to paycheck_anchor_day.
    """
    with get_db_connection() as conn:
        anchor_row = conn.execute(
            "SELECT paycheck_anchor_day FROM global_settings WHERE person_id = ?",
            (person_id,),
        ).fetchone()
        anchor_day = anchor_row[0] if anchor_row else 10

        row = conn.execute(
            "SELECT max(paycheck_date) FROM paycheck_metadata WHERE person_id = ?",
            (person_id,),
        ).fetchone()

    cycle_start, _ = calculate_active_cycle(anchor_day)
    if row and row[0]:
        last_paycheck = datetime.strptime(row[0], "%Y-%m-%d").date()
        if last_paycheck + relativedelta(months=1) > date.today():
            cycle_start = last_paycheck

    return cycle_start
