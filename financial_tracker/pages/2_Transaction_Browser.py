# /// script
# dependencies = [
#     "streamlit",
#     "pandas",
#     "python-dateutil",
# ]
# ///
"""Transaction ledger, in two resolutions.

**By receipt** is the old one-row-per-shopping-trip view. **By item** breaks each
receipt open so a lamp bought inside a mixed Kaufland trip is its own row, with its
own macro/micro and its own budget line — which is the only way to answer "what did I
actually buy for the household this cycle?".

Both views route spending to budget lines exactly the way the dashboard does
(category_mapping, unmapped macros falling back to groceries), so a filtered total
here reconciles against the bar you clicked through from.
"""
import sqlite3
from datetime import date

import pandas as pd
import streamlit as st
from dateutil.relativedelta import relativedelta

from auth import flask_base_url, get_current_user_id
from cycle import get_current_cycle_start
from schema import get_db_connection, init_schema

ALL = "All"
MIXED = "Mixed"
NO_ITEMS = "—"
MANUAL_ITEM_LABEL = "— whole expense —"
LINE_SEPARATOR = "|"
CUSTOM = "Custom…"

# Shared by both views: an item's budget line is its macro's mapping, or groceries.
# Mirrors get_budget_status() in streamlit_app.py — if that fallback ever changes,
# it has to change in both places or the totals here stop matching the bars there.
_ITEM_BUDGET_LINE = """
        LEFT JOIN category_mapping cm
            ON cm.macro_category = i.macro_category AND cm.person_id = r.person_id
        LEFT JOIN budget_categories bc ON bc.id = cm.category_id
"""


def get_item_ledger(person_id, start_date, end_date):
    """One row per scanned item, plus one row per manual expense."""
    query = f"""
    -- Source A: individual lines off scanned receipts
    SELECT
        r.shopping_date AS "Date",
        r.shop_name AS "Merchant",
        i.name AS "Item",
        i.macro_category AS "Macro",
        i.micro_category AS "Micro",
        LOWER(COALESCE(bc.category_name, 'groceries')) AS "Budget Line",
        -- i.price is already the line total (quantity x unit price), per sqlite_db.save_receipt
        i.price AS "Amount (€)",
        'Automated (OCR)' AS "Source",
        r.receipt_id AS "_receipt_id",
        NULL AS "_expense_id"
    FROM item i
    JOIN receipt r ON r.receipt_id = i.receipt_id
    {_ITEM_BUDGET_LINE}
    WHERE r.person_id = ? AND r.shopping_date BETWEEN ? AND ?

    UNION ALL

    -- Source B: manual expenses have no line items, so each is a single row. Included
    -- so a filtered total here matches the dashboard bar, which counts both sources.
    SELECT
        me.date,
        me.description,
        '{MANUAL_ITEM_LABEL}',
        NULL,
        NULL,
        LOWER(bc.category_name),
        me.amount,
        'Manual',
        NULL,
        me.expense_id
    FROM manual_expenses me
    JOIN budget_categories bc ON bc.id = me.category_id
    WHERE me.person_id = ? AND me.date BETWEEN ? AND ?

    ORDER BY "Date" DESC, "Merchant" ASC, "Item" ASC
    """
    with get_db_connection() as conn:
        return pd.read_sql_query(
            query, conn,
            params=(person_id, start_date, end_date, person_id, start_date, end_date),
        )


def get_receipt_ledger(person_id, start_date, end_date):
    """One row per shopping trip.

    A receipt spanning several budget lines is labelled "Mixed" rather than claiming
    one of them: the old query selected i.macro_category while grouping by receipt, so
    SQLite picked an arbitrary item's category for the whole trip. "_all_lines" keeps
    every line the receipt touches so filtering can still reach inside a mixed trip.
    """
    query = f"""
    WITH receipt_lines AS (
        SELECT
            receipt_id,
            GROUP_CONCAT(budget_line, '{LINE_SEPARATOR}') AS lines_concat,
            COUNT(*) AS line_count
        FROM (
            SELECT DISTINCT
                r.receipt_id AS receipt_id,
                LOWER(COALESCE(bc.category_name, 'groceries')) AS budget_line
            FROM item i
            JOIN receipt r ON r.receipt_id = i.receipt_id
            {_ITEM_BUDGET_LINE}
            WHERE r.person_id = ?
        )
        GROUP BY receipt_id
    )
    SELECT
        r.shopping_date AS "Date",
        r.shop_name AS "Merchant",
        GROUP_CONCAT(i.name, ', ') AS "Details",
        r.total AS "Amount (€)",
        CASE
            WHEN rl.line_count > 1 THEN '{MIXED}'
            ELSE COALESCE(rl.lines_concat, '{NO_ITEMS}')
        END AS "Category",
        COALESCE(rl.lines_concat, '') AS "_all_lines",
        'Automated (OCR)' AS "Source",
        r.receipt_id AS "_receipt_id",
        NULL AS "_expense_id"
    FROM receipt r
    LEFT JOIN item i ON i.receipt_id = r.receipt_id
    LEFT JOIN receipt_lines rl ON rl.receipt_id = r.receipt_id
    WHERE r.person_id = ? AND r.shopping_date BETWEEN ? AND ?
    GROUP BY r.receipt_id

    UNION ALL

    SELECT
        me.date,
        me.description,
        'Manual Entry',
        me.amount,
        LOWER(bc.category_name),
        LOWER(bc.category_name),
        'Manual',
        NULL,
        me.expense_id
    FROM manual_expenses me
    JOIN budget_categories bc ON bc.id = me.category_id
    WHERE me.person_id = ? AND me.date BETWEEN ? AND ?

    ORDER BY "Date" DESC, "Merchant" ASC
    """
    with get_db_connection() as conn:
        return pd.read_sql_query(
            query, conn,
            params=(person_id, person_id, start_date, end_date, person_id, start_date, end_date),
        )


def delete_manual_expense(person_id, expense_id):
    """Delete one manual expense. Scoped to its owner: expense_id is a guessable
    integer, so ownership is part of the WHERE clause rather than a prior check.
    Returns True if a row was actually removed."""
    with get_db_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM manual_expenses WHERE expense_id = ? AND person_id = ?",
            (expense_id, person_id),
        )
        conn.commit()
        return cursor.rowcount > 0


def manage_url(receipt_id):
    """Deep link into the Flask receipt manager, focused on one receipt.

    Root-relative behind Caddy, absolute against the Flask dev server otherwise —
    see flask_base_url().
    """
    if pd.isna(receipt_id):
        return None
    return f"{flask_base_url()}/receipts?focus={int(receipt_id)}"


def get_budget_lines(person_id):
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT LOWER(category_name) FROM budget_categories WHERE person_id = ? "
            "ORDER BY category_name",
            (person_id,),
        ).fetchall()
    return [row[0] for row in rows]


def resolve_range(preset, person_id):
    """Turn a preset label into (start, end) dates. None means 'ask the user'."""
    cycle_start = get_current_cycle_start(person_id)
    if preset == "Current cycle":
        return cycle_start, cycle_start + relativedelta(months=1) - relativedelta(days=1)
    if preset == "Last 3 months":
        return date.today() - relativedelta(months=3), date.today()
    if preset == "Last 6 months":
        return date.today() - relativedelta(months=6), date.today()
    if preset == "Last 12 months":
        return date.today() - relativedelta(months=12), date.today()
    if preset == "All time":
        return date(2000, 1, 1), date.today() + relativedelta(years=1)
    return None, None


# --- UI INITIALIZATION ---
st.set_page_config(page_title="Transaction Ledger", layout="wide")
st.title("🔍 Transaction Ledger Browser")
st.caption("Browse, search, and analyze all expenses across your shared account and personal budgets.")

user_id = get_current_user_id()
with get_db_connection() as conn:
    init_schema(conn)

# --- VIEW + DATE RANGE ---
col_view, col_preset = st.columns([1, 1])

with col_view:
    view = st.radio(
        "View",
        ["By receipt", "By item"],
        horizontal=True,
        help="'By item' lists every scanned line separately, so a household purchase "
             "inside a mixed grocery receipt is visible on its own.",
    )

with col_preset:
    preset = st.selectbox(
        "Date range",
        ["Current cycle", "Last 3 months", "Last 6 months", "Last 12 months", "All time", CUSTOM],
        help="Defaults to the active budget cycle, so totals line up with the dashboard bars.",
    )

start_date, end_date = resolve_range(preset, user_id)
if start_date is None:
    col_from, col_to = st.columns(2)
    cycle_start = get_current_cycle_start(user_id)
    with col_from:
        start_date = st.date_input("From", value=cycle_start)
    with col_to:
        end_date = st.date_input("To", value=date.today())
    if start_date > end_date:
        st.error("The start of the range is after its end.")
        st.stop()

start_str = start_date.strftime("%Y-%m-%d")
end_str = end_date.strftime("%Y-%m-%d")
item_view = view == "By item"

# Load the ledger at the chosen resolution
try:
    if item_view:
        df_ledger = get_item_ledger(user_id, start_str, end_str)
    else:
        df_ledger = get_receipt_ledger(user_id, start_str, end_str)
except sqlite3.OperationalError:
    st.error("Make sure your database schema is initialized and you have run a few transactions first!")
    st.stop()

# --- FILTERING ZONE ---
st.subheader("🛠️ Filters")

budget_lines = get_budget_lines(user_id)

if item_view:
    col_search, col_line, col_macro, col_micro, col_src = st.columns([2, 1, 1, 1, 1])
else:
    col_search, col_line, col_src = st.columns([2, 1, 1])
    col_macro = col_micro = None

with col_search:
    search_query = st.text_input(
        "🔍 Search Merchant or Item" if item_view else "🔍 Search Merchant or Details",
        placeholder="e.g., Lidl, Mortgage, OMV...",
    )

with col_line:
    selected_line = st.selectbox(
        "Budget Line", [ALL] + budget_lines,
        help="Where the spend counts on the dashboard, via the macro routing in Configuration.",
    )

selected_macro = selected_micro = ALL
if item_view:
    with col_macro:
        macros = sorted(df_ledger["Macro"].dropna().unique().tolist())
        selected_macro = st.selectbox("Macro Category", [ALL] + macros)

    with col_micro:
        # Micro options narrow to the chosen macro — the full list spans hundreds of values.
        micro_pool = df_ledger
        if selected_macro != ALL:
            micro_pool = micro_pool[micro_pool["Macro"] == selected_macro]
        micros = sorted(micro_pool["Micro"].dropna().unique().tolist())
        selected_micro = st.selectbox("Micro Category", [ALL] + micros)

with col_src:
    selected_source = st.selectbox("Filter by Ingestion Source", [ALL, "Automated (OCR)", "Manual"])

# --- FILTER APPLICATION LOGIC ---
filtered_df = df_ledger.copy()

if search_query:
    text_column = "Item" if item_view else "Details"
    filtered_df = filtered_df[
        filtered_df["Merchant"].str.contains(search_query, case=False, na=False)
        | filtered_df[text_column].str.contains(search_query, case=False, na=False)
    ]

if selected_line != ALL:
    if item_view:
        filtered_df = filtered_df[filtered_df["Budget Line"] == selected_line]
    else:
        # A mixed receipt matches every line it contains, so filtering by household
        # surfaces the Kaufland trip that held one lamp instead of dropping it.
        filtered_df = filtered_df[
            filtered_df["_all_lines"].apply(
                lambda lines: selected_line in str(lines).split(LINE_SEPARATOR)
            )
        ]

if selected_macro != ALL:
    filtered_df = filtered_df[filtered_df["Macro"] == selected_macro]

if selected_micro != ALL:
    filtered_df = filtered_df[filtered_df["Micro"] == selected_micro]

if selected_source != ALL:
    filtered_df = filtered_df[filtered_df["Source"] == selected_source]

# --- LEDGER DISPLAY ---
st.markdown("---")

if filtered_df.empty:
    st.info("No transactions found matching the selected criteria.")
    st.stop()

m_count, m_total, m_range = st.columns(3)
m_count.metric("Items Shown" if item_view else "Transactions Shown", len(filtered_df))
m_total.metric("Total Sum", f"€{filtered_df['Amount (€)'].sum():.2f}")
m_range.metric(
    "Range",
    preset if preset != CUSTOM else "Custom",
    help=f"{start_str} → {end_str}",
)

if not item_view and selected_line != ALL:
    st.caption(
        f"⚠️ Receipt totals are whole trips. A **{MIXED}** row shown here counts toward "
        f"*{selected_line}* only for the items inside it that route there — switch to "
        "**By item** for a total that reconciles against the dashboard."
    )

# One deep link per scanned row; manual rows get no link (they are deleted right here).
filtered_df = filtered_df.copy()
filtered_df["Manage"] = filtered_df["_receipt_id"].apply(manage_url)

column_config = {
    "Date": st.column_config.DateColumn("Date", format="YYYY-MM-DD"),
    "Amount (€)": st.column_config.NumberColumn("Amount", format="€%.2f"),
    "Source": st.column_config.TextColumn("Type"),
    "Manage": st.column_config.LinkColumn(
        "Manage", display_text="open ↗", width="small",
        help="Open this receipt in the Receipt Manager, where it can be edited or deleted.",
    ),
}

# Helper columns exist for filtering and for the action panel, not for display.
display_df = filtered_df.drop(
    columns=["_all_lines", "_receipt_id", "_expense_id"], errors="ignore"
).reset_index(drop=True)

selection = st.dataframe(
    display_df,
    use_container_width=True,
    column_config=column_config,
    hide_index=True,
    on_select="rerun",
    selection_mode="single-row",
)

# --- ROW ACTIONS ---
# Only manual expenses are deleted here. A scanned receipt is items *plus* a scan row
# *plus* an image on disk, and Flask's /delete-receipt is the only place that knows all
# three — so those link out rather than being deleted behind its back.
selected_rows = selection.selection.rows if selection and selection.selection else []
if not selected_rows:
    st.caption("Select a row to delete a manual expense, or open a scanned receipt.")
else:
    row = filtered_df.reset_index(drop=True).iloc[selected_rows[0]]
    label = f"{row['Merchant']} · €{row['Amount (€)']:.2f} · {row['Date']}"

    if row["Source"] == "Manual":
        expense_id = int(row["_expense_id"])
        st.warning(f"**{label}** — manual expense.")
        confirm = st.checkbox(
            "Yes, delete it permanently", key=f"confirm_delete_{expense_id}",
            help="Deletion cannot be undone.",
        )
        if st.button("🗑 Delete manual expense", type="primary", disabled=not confirm):
            deleted = delete_manual_expense(user_id, expense_id)
            if deleted:
                st.success(f"Deleted {label}.")
            else:
                st.error("That expense no longer exists, or is not yours.")
            st.rerun()
    else:
        st.info(
            f"**{label}** — scanned receipt. Deleting it also removes its items and the "
            "stored receipt image, which happens in the Receipt Manager."
        )
        st.link_button("Open in Receipt Manager ↗", manage_url(row["_receipt_id"]))
