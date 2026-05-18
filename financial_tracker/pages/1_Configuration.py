# /// script
# dependencies = [
#     "streamlit",
#     "pandas",
# ]
# ///
import streamlit as st
import pandas as pd
import sqlite3
from datetime import date

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
    CREATE TABLE IF NOT EXISTS paycheck_metadata (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        person_id INTEGER NOT NULL,
        paycheck_date DATE NOT NULL
    )""")
    conn.commit()

# Paycheck Target Setup
st.subheader("📅 Set Paycheck Anchor Date")
with get_db_connection() as conn:
    row = conn.execute("SELECT max(paycheck_date) FROM paycheck_metadata WHERE person_id = 1").fetchone()
st.info(f"Current financial tracking period starts from: **{row[0] if row and row[0] else 'Not set'}**")

with st.form("paycheck_form"):
    new_date = st.date_input("Last Paycheck Date", date.today())
    if st.form_submit_button("Update Paycheck Anchor"):
        with get_db_connection() as conn:
            conn.execute("INSERT INTO paycheck_metadata (person_id, paycheck_date) VALUES (1, ?)", (new_date.strftime("%Y-%m-%d"),))
            conn.commit()
        st.success("Anchor updated!")
        st.rerun()

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