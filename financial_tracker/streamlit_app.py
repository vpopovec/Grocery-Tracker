# /// script
# dependencies = [
#     "streamlit",
#     "pandas",
# ]
# ///
import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date
import traceback

DB_PATH = "../receipts.db"  # Path to your existing SQLite database

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn

def get_current_user_id():
    # Hardcoded to your person_id for the local POC
    return 1 

def get_budget_status(person_id):
    # Aggregates both Gemini OCR line-items and manual entries since the last paycheck
    query = """
    WITH current_cycle AS (
        SELECT COALESCE(max(paycheck_date), '1970-01-01') as start_date 
        FROM paycheck_metadata 
        WHERE person_id = ?
    )
    SELECT 
        bc.category_name,
        bc.monthly_limit,
        bc.is_personal,
        COALESCE(SUM(i.price * COALESCE(i.amount, 1)), 0) as total_spent
    FROM budget_categories bc
    CROSS JOIN current_cycle cc
    LEFT JOIN item i ON LOWER(i.macro_category) = LOWER(bc.category_name)
    LEFT JOIN receipt r ON i.receipt_id = r.receipt_id AND r.shopping_date >= cc.start_date
    GROUP BY bc.category_name, bc.monthly_limit, bc.is_personal
    """
    with get_db_connection() as conn:
        return pd.read_sql_query(query, conn, params=(person_id,))

def get_days_until_next_paycheck(person_id):
    with get_db_connection() as conn:
        row = conn.execute("SELECT max(paycheck_date) FROM paycheck_metadata WHERE person_id = ?", (person_id,)).fetchone()
        if not row or not row[0]:
            return 30
        last_paycheck = datetime.strptime(row[0], "%Y-%m-%d").date()
        if last_paycheck.month == 12:
            next_paycheck = date(last_paycheck.year + 1, 1, last_paycheck.day)
        else:
            next_paycheck = date(last_paycheck.year, last_paycheck.month + 1, last_paycheck.day)
        
        return max((next_paycheck - date.today()).days, 1)

# --- UI ---
st.set_page_config(page_title="Finance Orchestrator", layout="wide")
st.title("📊 Family Financial Orchestrator")

user_id = get_current_user_id()

try:
    df_budgets = get_budget_status(user_id)
    days_left = get_days_until_next_paycheck(user_id)
except Exception as e:
    st.error("Database extensions uninitialized. Please go to the Configuration page first!")
    traceback.print_exc()
    st.stop()

col_dash, col_input = st.columns([2, 1], gap="large")

with col_dash:
    st.subheader("Personal Budgets")
    personal_df = df_budgets[df_budgets['is_personal'] == 1]
    
    if personal_df.empty:
        st.info("No personal budgets configured yet.")
    
    for _, row in personal_df.iterrows():
        limit = row['monthly_limit']
        spent = row['total_spent']
        
        # If limit is missing or zero, default it to 1.0 to prevent division errors, 
        # or handle it as an unconfigured budget.
        if pd.isna(limit) or limit <= 0:
            limit = 1.0

        remaining = max(limit - spent, 0.0)
        daily_allowance = remaining / days_left
        
        st.write(f"### {row['category_name'].title()}")
        m1, m2, m3 = st.columns(3)
        m1.metric("Remaining", f"€{remaining:.2f}")
        m2.metric("Daily Allowance", f"€{daily_allowance:.2f}/day")
        m3.metric("Spent", f"€{spent:.2f}")
        st.progress(min(spent / limit, 1.0))
        st.markdown("---")

with col_input:
    st.subheader("➕ Log Manual Expense")
    with st.form("manual_expense", clear_on_submit=True):
        tx_date = st.date_input("Date", date.today())
        tx_desc = st.text_input("Merchant/Description (e.g. Mortgage, OMV)")
        tx_amount = st.number_input("Total Amount (€)", min_value=0.0, step=0.01)
        
        # Pull category options dynamically from configuration table
        cat_list = df_budgets['category_name'].tolist()
        tx_cat = st.selectbox("Budget Category", cat_list if cat_list else ["Setup Required"])
        
        if st.form_submit_button("Save Expense") and tx_amount > 0:
            with get_db_connection() as conn:
                # 1. Create a dummy receipt header
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO receipt (person_id, shop_name, total, shopping_date, llm_elapsed_seconds)
                    VALUES (?, ?, ?, ?, 0.0)
                """, (user_id, tx_desc, tx_amount, tx_date.strftime("%Y-%m-%d")))
                receipt_id = cursor.lastrowid
                
                # 2. Insert line item matching the macro_category name
                cursor.execute("""
                    INSERT INTO item (price, amount, name, macro_category, micro_category, receipt_id)
                    VALUES (?, 1.0, ?, ?, 'manual', ?)
                """, (tx_amount, tx_desc, tx_cat, receipt_id))
                conn.commit()
                
            st.success(f"Logged €{tx_amount:.2f} under {tx_cat}!")
            st.rerun()