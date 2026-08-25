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

from auth import get_current_user_id
from cycle import calculate_active_cycle
from schema import get_db_connection, init_schema, macro_categories, seed_defaults

st.set_page_config(page_title="Configuration", layout="wide")
st.title("⚙️ Budget Configuration")

# Initialize extension tables seamlessly
with get_db_connection() as conn:
    init_schema(conn)

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



st.header("💳 Paycheck & Budget Cycle Sync")

user_id = get_current_user_id()

with get_db_connection() as conn:
    seed_defaults(conn, user_id)

# 1. Fetch current anchor configuration from database
with get_db_connection() as conn:
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
st.subheader("🏷️ Budget Lines")
st.caption(
    "One row per budget line. Tick **Monthly goal** for a line you want to spend *at least* "
    "the limit on (household investment) instead of staying under it — its bar fills up as you "
    "spend and turns green once the goal is met."
)

with get_db_connection() as conn:
    df_cat = pd.read_sql_query(
        "SELECT id, category_name, is_personal, is_goal, monthly_limit "
        "FROM budget_categories WHERE person_id = ? ORDER BY id",
        conn, params=(user_id,),
    )

df_cat['is_personal'] = df_cat['is_personal'].fillna(0).astype(bool)
df_cat['is_goal'] = df_cat['is_goal'].fillna(0).astype(bool)

edited_df = st.data_editor(
    df_cat,
    num_rows="dynamic",
    column_config={
        "id": st.column_config.NumberColumn("ID", disabled=True),
        "category_name": st.column_config.TextColumn("Category Name (Lowercase recommended)", required=True),
        "is_personal": st.column_config.CheckboxColumn("Is Personal Budget?"),
        "is_goal": st.column_config.CheckboxColumn("Monthly goal?", help="Spend at least this much, rather than at most"),
        "monthly_limit": st.column_config.NumberColumn("Monthly Limit / Goal (€)", min_value=0),
        "person_id": None  # <─── This completely hides the column from the UI while keeping it in the dataframe
    },
    key="editor"
)

if st.button("Save Changes"):
    # Convert bools back to integers safely
    edited_df['is_personal'] = edited_df['is_personal'].fillna(False).astype(int)
    edited_df['is_goal'] = edited_df['is_goal'].fillna(False).astype(int)

    with get_db_connection() as conn:
        # 1. Collect all valid IDs currently inside the Streamlit editor dataframe
        # (New rows won't have an ID or it will be NaN)
        valid_ids = edited_df['id'].dropna().astype(int).tolist()

        # 2. Delete any categories from the database that the user removed in the editor.
        #    Scoped to this person: the editor only ever showed their own rows, so an
        #    unscoped NOT IN would take everyone else's categories with it.
        if valid_ids:
            placeholders = ",".join(["?"] * len(valid_ids))
            conn.execute(
                f"DELETE FROM budget_categories WHERE person_id = ? AND id NOT IN ({placeholders})",
                (user_id, *valid_ids),
            )
        else:
            conn.execute("DELETE FROM budget_categories WHERE person_id = ?", (user_id,))

        # 3. Step through rows and Upsert them individually
        for _, row in edited_df.iterrows():
            category_id = row.get('id')
            
            # Handle empty monthly limits safely for SQLite (NaN -> None)
            limit = None if pd.isna(row['monthly_limit']) else float(row['monthly_limit'])
            
            if pd.isna(category_id):
                # This is a brand new row added via the "+" button
                conn.execute("""
                    INSERT INTO budget_categories (category_name, is_personal, is_goal, monthly_limit, person_id)
                    VALUES (?, ?, ?, ?, ?)
                """, (row['category_name'], row['is_personal'], row['is_goal'], limit, user_id))
            else:
                # This is an existing row -> Update it!
                conn.execute("""
                    UPDATE budget_categories 
                    SET category_name = ?, is_personal = ?, is_goal = ?, monthly_limit = ?
                    WHERE id = ? AND person_id = ?
                """, (row['category_name'], row['is_personal'], row['is_goal'], limit,
                      int(category_id), user_id))
                
        conn.commit()
        
    st.success("Configurations successfully updated!")
    st.rerun()

st.markdown("---")

# ─── MACRO → BUDGET ROUTING ───
st.subheader("🧭 Route Scanned Items to Budget Lines")
st.caption(
    "Every scanned receipt item carries a macro category. This is where each macro lands on "
    "the dashboard. Unmapped macros fall back to *groceries*."
)

with get_db_connection() as conn:
    df_budget_names = pd.read_sql_query(
        "SELECT id, category_name FROM budget_categories WHERE person_id = ? ORDER BY category_name",
        conn, params=(user_id,),
    )
    df_map = pd.read_sql_query(
        "SELECT macro_category, category_id FROM category_mapping WHERE person_id = ?",
        conn, params=(user_id,),
    )

if df_budget_names.empty:
    st.warning("Add at least one budget line above before routing macro categories.")
else:
    UNMAPPED = "— unmapped (groceries) —"
    id_to_name = dict(zip(df_budget_names['id'], df_budget_names['category_name']))
    name_to_id = {name: cat_id for cat_id, name in id_to_name.items()}
    current = dict(zip(df_map['macro_category'], df_map['category_id']))

    # Driven by the taxonomy, so a macro added in taxonomy.py shows up here automatically.
    df_routing = pd.DataFrame({
        "macro_category": macro_categories(),
        "budget_line": [id_to_name.get(current.get(macro), UNMAPPED) for macro in macro_categories()],
    })

    edited_routing = st.data_editor(
        df_routing,
        hide_index=True,
        column_config={
            "macro_category": st.column_config.TextColumn("Item Macro Category", disabled=True),
            "budget_line": st.column_config.SelectboxColumn(
                "Counts Toward", options=[UNMAPPED] + list(name_to_id), required=True),
        },
        key="routing_editor",
    )

    if st.button("Save Routing"):
        with get_db_connection() as conn:
            for _, row in edited_routing.iterrows():
                macro = row['macro_category']
                category_id = name_to_id.get(row['budget_line'])
                if category_id is None:
                    conn.execute(
                        "DELETE FROM category_mapping WHERE person_id = ? AND macro_category = ?",
                        (user_id, macro),
                    )
                else:
                    conn.execute("""
                        INSERT INTO category_mapping (person_id, macro_category, category_id)
                        VALUES (?, ?, ?)
                        ON CONFLICT(person_id, macro_category)
                        DO UPDATE SET category_id = excluded.category_id
                    """, (user_id, macro, int(category_id)))
            conn.commit()
        st.success("Routing saved!")
        st.rerun()