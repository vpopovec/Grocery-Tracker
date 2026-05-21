# /// script
# dependencies = [
#     "streamlit",
#     "pandas",
#     "python-dateutil",
# ]
# ///
import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date
import traceback
from dateutil.relativedelta import relativedelta

DB_PATH = "../receipts.db"


def calculate_active_cycle(anchor_day=10):
    today = date.today()
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
        return pd.read_sql_query(query, conn, params=(person_id, computed_start_str, person_id, person_id, person_id))


def get_days_until_next_paycheck(person_id):
    """
    Looks up the most recent paycheck milestone to calculate the remaining calendar
    days until the next monthly injection drops.
    """
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


# --- UI SETUP & RUNWAY TEXT CODES ---
st.set_page_config(page_title="Finance Orchestrator", layout="centered")

st.markdown(
    """
    <style>
    /* --- NEW: COMPACT TOP HEADER GAP OVERRIDES --- */
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 1rem !important;
    }
    /* Update the H1 element layout to completely center your family logo title string */
    h1 {
        text-align: center !important;
        margin-bottom: 0.5rem !important;
        padding-bottom: 0px !important;
    }
    [data-testid="stHeader"] {
        height: 2rem !important;
        background: transparent !important;
    }

    /* --- EXISTING LIST ROW SYSTEM --- */
    .compact-category-container {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        display: flex;
        flex-direction: column;
        gap: 8px;
        width: 100%;
        margin-top: 15px;
    }
    .compact-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 10px 12px;
        background-color: rgba(255, 255, 255, 0.04);
        border-radius: 8px;
        font-size: 0.9rem;
        white-space: nowrap;
    }
    .cat-name {
        font-weight: 600;
        width: 30%;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .progress-bar-bg {
        flex-grow: 1;
        height: 10px;
        background-color: rgba(255, 255, 255, 0.08);
        border-radius: 6px;
        margin: 0 16px;
        position: relative;
        overflow: hidden;
    }
    .progress-bar-fill {
        height: 100%;
        border-radius: 6px;
        transition: width 0.4s ease;
    }
    .cat-metrics {
        font-variant-numeric: tabular-nums;
        text-align: right;
        width: 35%;
        font-size: 0.85rem;
    }
    .metric-remaining { font-weight: 700; }
    .metric-total { opacity: 0.5; font-size: 0.8rem; }

    /* Disable focus and text input capabilities on the text node directly */
    div[data-testid="stSidebar"] div[data-testid="stDateInput"] input[data-testid="stDateInputField"] {
        pointer-events: none !important;
        caret-color: transparent !important;
        user-select: none !important;
        -webkit-user-select: none !important; /* Safari support */
    }

    /* Ensure the parent block still receives the tap to open the calendar picker */
    div[data-testid="stSidebar"] div[data-testid="stDateInput"] > div {
        cursor: pointer !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("👨‍👩‍👧 V+M+V 💰")
user_id = get_current_user_id()

try:
    df_budgets = get_budget_status(user_id)
    # ─── EXTRACTION STEP: Pull your days left metrics cleanly from your DB engine
    days_left = get_days_until_next_paycheck(user_id)
except Exception as e:
    st.error("Database connections uninitialized.")
    st.stop()


# --- 1. NEW: PAYCHECK COUNTDOWN RUNWAY ---
# This acts as a high-level timeline tracker sitting comfortably above your targets
total_cycle_days = 30 # Standard fallback cycle length context
days_pct = max(min((days_left / total_cycle_days), 1.0), 0.0)

# The timeline bar remains a clean, neutral blue so it doesn't clash with budget alerts
timeline_html = f"""
<div style="margin-bottom: 25px; background-color: rgba(255, 255, 255, 0.02); padding: 12px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; font-size: 0.9rem;">
        <span style="font-weight: 600; opacity: 0.9;">⏳ Paycheck Timeline</span>
        <span style="font-weight: 700; color: #60a5fa;">{days_left} days remaining</span>
    </div>
    <div class="progress-bar-bg" style="margin: 0; height: 8px;">
        <div class="progress-bar-fill" style="width: {days_pct*100}%; background: linear-gradient(90deg, #3b82f6 0%, #60a5fa 100%);"></div>
    </div>
</div>
"""
st.html(timeline_html)

# --- MAIN RUNWAY CONTENT DISPLAY ---
st.subheader("Budget Status")

html_rows = []
for _, row in df_budgets.iterrows():
    name = str(row['category_name']).title()
    spent = float(row['total_spent'])
    limit = float(row['monthly_limit'])
    
    remaining = max(limit - spent, 0.0)
    pct = max((remaining / limit), 0.0) if limit > 0 else 0.0
    
    if pct <= 0.15:
        color = "#ff4b4b"  # Danger Warning Red (15% or less runway left)
    elif pct <= 0.40:
        color = "#faca15"  # Cautionary Yellow
    else:
        color = "#22c55e"  # Safe Runway Green
        
    html_rows.append(f"""
    <div class="compact-row">
        <div class="cat-name">{name}</div>
        <div class="progress-bar-bg">
            <div class="progress-bar-fill" style="width: {pct*100}%; background-color: {color};"></div>
        </div>
        <div class="cat-metrics">
            <span class="metric-remaining" style="color: {color if pct <= 0.40 else 'inherit'}">{remaining:.0f} € left</span>
            <span class="metric-total">/ {limit:.0f} €</span>
        </div>
    </div>
    """)
    
full_table_html = f'<div class="compact-category-container">{"".join(html_rows)}</div>'
st.html(full_table_html)


# --- THE NEW SIDEBAR FORM NAVIGATION PATTERN ---
# Moving components here completely isolates widget states and resolves the focus bug natively
with st.sidebar:
    st.subheader("➕ Log Manual Expense")
    
    with st.form("sidebar_expense_form", clear_on_submit=True):
        # 🛡️ Clean, standard date input. The CSS at the top of the file stops the mobile keyboard.
        tx_date = st.date_input("Date", date.today())
        
        tx_desc = st.text_input("Merchant/Description (e.g. Billa, OMV)")
        tx_amount = st.number_input("Total Amount (€)", min_value=0.0, step=0.01)
        
        if not df_budgets.empty:
            cat_mapping = dict(zip(df_budgets['category_name'].str.title(), df_budgets['category_id']))
            cat_options = list(cat_mapping.keys())
        else:
            cat_options = ["Setup Required"]
            cat_mapping = {}
            
        tx_cat_name = st.selectbox("Budget Category", cat_options)
        
        if st.form_submit_button("Save Expense", use_container_width=True) and tx_amount > 0:
            if tx_cat_name != "Setup Required":
                chosen_category_id = int(cat_mapping[tx_cat_name])
                with get_db_connection() as conn:
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
                st.success(f"Logged €{tx_amount:.2f} successfully!")
                st.rerun()