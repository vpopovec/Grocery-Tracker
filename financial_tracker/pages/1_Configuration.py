# /// script
# dependencies = [
#     "streamlit",
#     "pandas",
# ]
# ///
import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

DB_PATH = "../receipts.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

st.set_page_config(page_title="Configuration", layout="wide")
st.title("⚙️ Budget Configuration")

# Initialize extension tables seamlessly
with get_db_connection() as conn:
    conn.execute("""
    CREATE TABLE IF NOT EXISTS budget_categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category_name TEXT UNIQUE NOT NULL,
        is_personal BOOLEAN DEFAULT 0,
        monthly_limit REAL NULL,
        person_id integer NOT NULL DEFAULT 1,
        FOREIGN KEY (person_id) REFERENCES person (person_id)
    )""")
    conn.execute("""
    -- Table A: A single-row global settings configuration table
    CREATE TABLE IF NOT EXISTS global_settings (
        person_id INTEGER PRIMARY KEY,
        paycheck_anchor_day INTEGER NOT NULL DEFAULT 10,
        FOREIGN KEY (person_id) REFERENCES person (person_id)
    )""")
    conn.execute("""
    -- Table B: Realized historical cycles (if you manually override a month)
    CREATE TABLE IF NOT EXISTS paycheck_metadata (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        person_id INTEGER NOT NULL,
        paycheck_date DATE NOT NULL UNIQUE, -- Year-Month tracking point
        FOREIGN KEY (person_id) REFERENCES person (person_id)
    )""")
    conn.commit()

# # Paycheck Target Setup
# st.subheader("📅 Set Paycheck Anchor Date")
# with get_db_connection() as conn:
#     row = conn.execute("SELECT max(paycheck_date) FROM paycheck_metadata WHERE person_id = 1").fetchone()
# st.info(f"Current financial tracking period starts from: **{row[0] if row and row[0] else 'Not set'}**")

# with st.form("paycheck_form"):
#     new_date = st.date_input("Last Paycheck Date", date.today())
#     if st.form_submit_button("Update Paycheck Anchor"):
#         with get_db_connection() as conn:
#             conn.execute("INSERT INTO paycheck_metadata (person_id, paycheck_date) VALUES (1, ?)", (new_date.strftime("%Y-%m-%d"),))
#             conn.commit()
#         st.success("Anchor updated!")
#         st.rerun()



def calculate_active_cycle(anchor_day=10):
    """
    Determines the start and end dates of the current cycle based on today's date.
    """
    today = date.today()
    
    # If we haven't reached the anchor day yet this month, 
    # our budget cycle started in the previous calendar month.
    if today.day < anchor_day:
        start_date = today - relativedelta(months=1)
        start_date = start_date.replace(day=anchor_day)
    else:
        start_date = today.replace(day=anchor_day)
        
    end_date = start_date + relativedelta(months=1) - relativedelta(days=1)
    return start_date, end_date


st.header("💳 Paycheck & Budget Cycle Sync")

user_id = 1

# 1. Fetch current anchor configuration from database
with get_db_connection() as conn:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS global_settings (
            person_id INTEGER PRIMARY KEY,
            paycheck_anchor_day INTEGER NOT NULL DEFAULT 10
        );
    """)
    row = conn.execute("SELECT paycheck_anchor_day FROM global_settings WHERE person_id = ?", (user_id,)).fetchone()
    current_anchor = row[0] if row else 10

# 2. Configurable interface input
col_anchor, col_save = st.columns([3, 1])
with col_anchor:
    new_anchor = st.number_input(
        "Standard Day of Month for Salary Ingestion", 
        min_value=1, max_value=31, value=current_anchor,
        help="The day you typically receive your paycheck. The budget limits reset here."
    )

with col_save:
    st.write(" ") # Structural vertical padding
    if st.button("Update Anchor"):
        with get_db_connection() as conn:
            conn.execute("""
                INSERT INTO global_settings (person_id, paycheck_anchor_day) 
                VALUES (?, ?)
                ON CONFLICT(person_id) DO UPDATE SET paycheck_anchor_day = excluded.paycheck_anchor_day
            """, (user_id, new_anchor))
            conn.commit()
        st.success("Anchor configuration synced!")
        st.rerun()

# ─── THE SMART LAYER: PREDICT CURRENT STATE ───
computed_start, computed_end = calculate_active_cycle(new_anchor)
days_total = (computed_end - computed_start).days + 1
days_spent = (date.today() - computed_start).days
days_left = max((computed_end - date.today()).days, 1)

st.markdown("---")
st.subheader("📊 Detected Budget Cycle State")

# Visual feedback box
st.info(f"📅 **Current Active Cycle:** {computed_start.strftime('%B %d, %Y')} to {computed_end.strftime('%B %d, %Y')}")

c1, c2, c3 = st.columns(3)
c1.metric("Days Elapsed", f"{days_spent} days", f"Started {computed_start.strftime('%b %d')}")
c2.metric("Days Remaining", f"{days_left} days", f"Ends {computed_end.strftime('%b %d')}")
c3.metric("Cycle Footprint", f"{days_total} Days Total")

# ─── OVERRIDE SECTION: WHEN REALITY DOESN'T MATCH THE ANCHOR ───
st.markdown("### ⚠️ Log Early/Late Paycheck Variance")
st.caption("Did your paycheck land early or late this month due to a holiday or weekend? Pin the precise date below to align metrics.")

with st.form("override_cycle"):
    actual_paycheck_date = st.date_input("Actual Paycheck Date", value=computed_start)
    
    if st.form_submit_button("Lock Cycle Ingress Date"):
        with get_db_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS paycheck_metadata (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    person_id INTEGER NOT NULL,
                    paycheck_date DATE NOT NULL UNIQUE
                );
            """)
            try:
                conn.execute(
                    "INSERT INTO paycheck_metadata (person_id, paycheck_date) VALUES (?, ?)", 
                    (user_id, actual_paycheck_date.strftime("%Y-%m-%d"))
                )
                conn.commit()
                st.success(f"Budget anchor locked for {actual_paycheck_date.strftime('%B %d')}!")
            except sqlite3.IntegrityError:
                st.warning("A paycheck entry already exists for this exact day.")

st.markdown("---")

# Categories Editor
st.subheader("🏷️ Map Macro Categories & Personal Budgets")
st.caption("Note: Ensure category names match exactly what Gemini outputs (e.g., 'groceries', 'cosmetics') or what you intend to track manually.")

with get_db_connection() as conn:
    df_cat = pd.read_sql_query("SELECT id, category_name, is_personal, monthly_limit FROM budget_categories", conn)

df_cat['is_personal'] = df_cat['is_personal'].astype(bool)

edited_df = st.data_editor(
    df_cat,
    num_rows="dynamic",
    column_config={
        "id": st.column_config.NumberColumn("ID", disabled=True),
        "category_name": st.column_config.TextColumn("Category Name (Lowercase recommended)", required=True),
        "is_personal": st.column_config.CheckboxColumn("Is Personal Budget?"),
        "monthly_limit": st.column_config.NumberColumn("Monthly Limit (€)", min_value=0),
        "person_id": None  # <─── This completely hides the column from the UI while keeping it in the dataframe
    },
    key="editor"
)

if st.button("Save Changes"):
    # Convert bools back to integers
    edited_df['is_personal'] = edited_df['is_personal'].fillna(False).astype(int)
    
    # Hardcoded to 1 for local POC, match with your current user system later
    edited_df['person_id'] = 1
    
    with get_db_connection() as conn:
        conn.execute("DELETE FROM budget_categories")
        edited_df.to_sql("budget_categories", conn, if_exists="append", index=False)
        conn.commit()
    st.success("Configurations successfully updated!")
    st.rerun()