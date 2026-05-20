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
from dateutil.relativedelta import relativedelta

DB_PATH = "../receipts.db"  # Path to your existing SQLite database


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


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn


# Initialize table seamlessly
with get_db_connection() as conn:
    conn.execute("""
    CREATE TABLE IF NOT EXISTS manual_expenses (
        expense_id INTEGER PRIMARY KEY AUTOINCREMENT,
        person_id INTEGER NOT NULL,
        date DATE NOT NULL,
        description TEXT NOT NULL,
        amount REAL NOT NULL,
        category_id INTEGER NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (person_id) REFERENCES person (person_id),
        FOREIGN KEY (category_id) REFERENCES budget_categories (id) ON DELETE CASCADE
    )
    """)


def get_current_user_id():
    # Hardcoded to your person_id for the local POC
    return 1 

def get_budget_status(person_id):
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT paycheck_anchor_day FROM global_settings WHERE person_id = ?", 
            (person_id,)
        ).fetchone()
        anchor_day = row[0] if row else 10

    computed_start_date, _ = calculate_active_cycle(anchor_day)
    computed_start_str = computed_start_date.strftime("%Y-%m-%d")

    query = """
    WITH current_cycle AS (
        SELECT COALESCE(
            (SELECT max(paycheck_date) FROM paycheck_metadata WHERE person_id = ?),
            ? 
        ) as start_date
    ),
    combined_spending AS (
        -- Source A: Automated OCR items with custom classification mapping
        SELECT 
            CASE 
                WHEN LOWER(i.macro_category) IN ('domácnosť', 'osobná hygiena a kozmetika', 'zdravie a drogéria') 
                     THEN 'cosmetics'
                ELSE 'groceries'
            END as cat_name,
            (i.price * COALESCE(i.amount, 1)) as total_item_cost
        FROM item i
        JOIN receipt r ON i.receipt_id = r.receipt_id
        CROSS JOIN current_cycle cc
        WHERE r.shopping_date >= cc.start_date AND r.person_id = ?
        
        UNION ALL
        
        -- Source B: Isolated manually logged expenses (mapped verbatim via category configuration)
        SELECT 
            LOWER(bc.category_name) as cat_name,
            me.amount as total_item_cost
        FROM manual_expenses me
        JOIN budget_categories bc ON me.category_id = bc.id
        CROSS JOIN current_cycle cc
        WHERE me.date >= cc.start_date AND me.person_id = ?
    )
    SELECT 
        bc.id as category_id,
        bc.category_name,
        bc.monthly_limit,
        bc.is_personal,
        COALESCE(SUM(cs.total_item_cost), 0) as total_spent
    FROM budget_categories bc
    LEFT JOIN combined_spending cs ON LOWER(cs.cat_name) = LOWER(bc.category_name)
    WHERE bc.person_id = ?
    GROUP BY bc.id, bc.category_name, bc.monthly_limit, bc.is_personal
    """
    
    with get_db_connection() as conn:
        return pd.read_sql_query(
            query, 
            conn, 
            params=(
                person_id,
                computed_start_str,
                person_id,
                person_id,
                person_id
            )
        )

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
    # --- PIPELINE RETRIEVAL ---
    df_budgets = get_budget_status(user_id)

    # ─── CALCULATE DAYS REMAINING IN CURRENT CYCLE ──────────────────────
    # We fetch the anchor to find out exactly where we are in the timeline
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT paycheck_anchor_day FROM global_settings WHERE person_id = ?", 
            (user_id,)
        ).fetchone()
        anchor_day = row[0] if row else 10

    _, computed_end = calculate_active_cycle(anchor_day)
    # Ensure days_left is at least 1 to eliminate any zero-division errors
    days_left = max((computed_end - date.today()).days, 1)
    # ────────────────────────────────────────────────────────────────────

    # Divide our single DataFrame into two targeted visual subsets
    personal_df = df_budgets[df_budgets['is_personal'] == 1]
    shared_df = df_budgets[df_budgets['is_personal'] == 0]

    # --- SECTION 1: PERSONAL BUDGETS ---
    st.header("👤 Personal Budgets")
    if personal_df.empty:
        st.info("No personal budget categories configured yet.")
    else:
        for _, row in personal_df.iterrows():
            limit = row['monthly_limit']
            spent = row['total_spent']
            
            has_no_limit = pd.isna(limit) or limit <= 0
            if has_no_limit:
                limit = 1.0  

            remaining = max(limit - spent, 0.0)
            # Calculate pace based on money left vs time left
            daily_allowance = remaining / days_left
            
            st.write(f"### {row['category_name'].title()}")
            m1, m2, m3 = st.columns(3)
            
            if has_no_limit:
                m1.metric("Remaining", "No Limit Set")
                m2.metric("Daily Allowance", "N/A")
            else:
                m1.metric("Remaining", f"€{remaining:.2f}")
                m2.metric("Daily Allowance", f"€{daily_allowance:.2f}/day")
                
            m3.metric("Spent", f"€{spent:.2f}")
            
            progress_val = min(spent / limit, 1.0)
            if pd.isna(progress_val): progress_val = 0.0
            st.progress(progress_val)


    # ─── SECTION 2: HOUSEHOLD & SHARED BUDGETS ────────────────────────
    st.markdown("---")
    st.header("🏠 Household & Shared Budgets")
    st.caption(f"Tracking shared allocations across your unified receipt scans. ({days_left} days left in cycle)")

    if shared_df.empty:
        st.info("No shared/household categories configured yet in Configuration.")
    else:
        for _, row in shared_df.iterrows():
            limit = row['monthly_limit']
            spent = row['total_spent']
            
            has_no_limit = pd.isna(limit) or limit <= 0
            if has_no_limit:
                limit = 1.0  
                
            remaining = max(limit - spent, 0.0)
            daily_allowance = remaining / days_left
            
            st.write(f"### {row['category_name'].title()}")
            col_rem, col_pace, col_spent = st.columns(3)
            
            if has_no_limit:
                col_rem.metric("Remaining", "No Cap Configured")
                col_pace.metric("Daily Allowance", "N/A")
            else:
                col_rem.metric("Remaining", f"€{remaining:.2f}")
                col_pace.metric("Daily Allowance", f"€{daily_allowance:.2f}/day")
                
            col_spent.metric("Total Spent", f"€{spent:.2f}")
            
            progress_val = min(spent / limit, 1.0)
            if pd.isna(progress_val): 
                progress_val = 0.0
                
            st.progress(progress_val)
            st.markdown(" ")

with col_input:
    st.subheader("➕ Log Manual Expense")
    with st.form("manual_expense", clear_on_submit=True):
        tx_date = st.date_input("Date", date.today())
        tx_desc = st.text_input("Merchant/Description (e.g. Mortgage, OMV)")
        tx_amount = st.number_input("Total Amount (€)", min_value=0.0, step=0.01)
        
        # ─── CHANGE: Create a dictionary mapping Name -> ID for dropdown selection ───
        # This assumes your df_budgets or df_categories contains 'category_id' (or 'id') and 'category_name'
        if not df_budgets.empty:
            cat_mapping = dict(zip(df_budgets['category_name'].str.title(), df_budgets['category_id']))
            cat_options = list(cat_mapping.keys())
        else:
            cat_options = ["Setup Required"]
            cat_mapping = {}
            
        tx_cat_name = st.selectbox("Budget Category", cat_options)
        
        if st.form_submit_button("Save Expense") and tx_amount > 0:
            if tx_cat_name == "Setup Required":
                st.error("Please set up categories in Configuration first!")
            else:
                chosen_category_id = int(cat_mapping[tx_cat_name])
                
                with get_db_connection() as conn:
                    # Make sure the table exists before attempting insertion
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS manual_expenses (
                            expense_id INTEGER PRIMARY KEY AUTOINCREMENT,
                            person_id INTEGER NOT NULL,
                            date DATE NOT NULL,
                            description TEXT NOT NULL,
                            amount REAL NOT NULL,
                            category_id INTEGER NOT NULL,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (person_id) REFERENCES person (person_id),
                            FOREIGN KEY (category_id) REFERENCES budget_categories (id) ON DELETE CASCADE
                        );
                    """)
                    
                    # ─── CHANGE: Clean, explicit insert into isolated table ───
                    conn.execute("""
                        INSERT INTO manual_expenses (person_id, date, description, amount, category_id)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        user_id, 
                        tx_date.strftime("%Y-%m-%d"), 
                        tx_desc, 
                        tx_amount, 
                        chosen_category_id
                    ))
                    conn.commit()
                    
                st.success(f"Logged €{tx_amount:.2f} under {tx_cat_name}!")
                st.rerun()
