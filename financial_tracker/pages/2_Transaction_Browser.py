# /// script
# dependencies = [
#     "streamlit",
#     "pandas",
# ]
# ///
import streamlit as st
import pandas as pd
import sqlite3

DB_PATH = "../receipts.db"  # Path to your existing SQLite database

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def get_all_transactions(person_id):
    # Aggregates automated items by receipt, and combines them with manual expenses
    query = """
    -- Source A: Automated OCR receipts (grouped to single row per trip)
    SELECT 
        r.shopping_date AS "Date",
        r.shop_name AS "Merchant",
        -- Concatenate items to give a quick summary without separate rows
        GROUP_CONCAT(i.name, ', ') AS "Details",
        r.total AS "Amount (€)",
        -- Pick the most frequent category or just flag as mixed/groceries
        COALESCE(LOWER(i.macro_category), 'groceries') AS "Category",
        'Automated (OCR)' AS "Source"
    FROM receipt r
    LEFT JOIN item i ON r.receipt_id = i.receipt_id
    WHERE r.person_id = ?
    GROUP BY r.receipt_id
    
    UNION ALL
    
    -- Source B: Manually logged expenses
    SELECT 
        me.date AS "Date",
        me.description AS "Merchant",
        'Manual Entry' AS "Details",
        me.amount AS "Amount (€)",
        LOWER(bc.category_name) AS "Category",
        'Manual' AS "Source"
    FROM manual_expenses me
    JOIN budget_categories bc ON me.category_id = bc.id
    WHERE me.person_id = ?
    
    ORDER BY "Date" DESC, "Merchant" ASC
    """
    with get_db_connection() as conn:
        return pd.read_sql_query(query, conn, params=(person_id, person_id))

# --- UI INITIALIZATION ---
st.set_page_config(page_title="Transaction Ledger", layout="wide")
st.title("🔍 Transaction Ledger Browser")
st.caption("Browse, search, and analyze all expenses across your shared account and personal budgets.")

# Mock user session state link
user_id = 1

# Load baseline ledger
try:
    df_ledger = get_all_transactions(user_id)
except sqlite3.OperationalError:
    st.error("Make sure your database schema is initialized and you have run a few transactions first!")
    st.stop()

# --- FILTERING ZONE (PLACEHOLDERS / EARLY ITERATION) ---
st.subheader("🛠️ Filters")

col_search, col_cat, col_src = st.columns([2, 1, 1])

with col_search:
    search_query = st.text_input("🔍 Search Merchant or Details", placeholder="e.g., Lidl, Mortgage, OMV...")

with col_cat:
    # Safely extract unique categories for filter drop-down
    unique_categories = ["All"] + sorted(df_ledger["Category"].unique().tolist()) if not df_ledger.empty else ["All"]
    selected_category = st.selectbox("Filter by Category", unique_categories)

with col_src:
    selected_source = st.selectbox("Filter by Ingestion Source", ["All", "Automated (OCR)", "Manual"])

# --- FILTER APPLICATION LOGIC ---
filtered_df = df_ledger.copy()

if search_query:
    filtered_df = filtered_df[
        filtered_df["Merchant"].str.contains(search_query, case=False, na=False) |
        filtered_df["Details"].str.contains(search_query, case=False, na=False)
    ]

if selected_category != "All":
    filtered_df = filtered_df[filtered_df["Category"] == selected_category]

if selected_source != "All":
    filtered_df = filtered_df[filtered_df["Source"] == selected_source]

# --- LEDGER DISPLAY ---
st.markdown("---")

if filtered_df.empty:
    st.info("No transactions found matching the selected criteria.")
else:
    # Summary Metrics for filtered view
    m_count, m_total = st.columns(2)
    m_count.metric("Transactions Shown", len(filtered_df))
    m_total.metric("Total Sum", f"€{filtered_df['Amount (€)'].sum():.2f}")
    
    # Render interactive clean grid view
    st.dataframe(
        filtered_df,
        use_container_width=True,
        column_config={
            "Date": st.column_config.DateColumn("Date", format="YYYY-MM-DD"),
            "Amount (€)": st.column_config.NumberColumn("Amount", format="€%.2f"),
            "Source": st.column_config.TextColumn("Type")
        },
        hide_index=True
    )