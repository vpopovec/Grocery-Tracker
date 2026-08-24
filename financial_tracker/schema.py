"""Schema bootstrap for the finance tracker's own tables.

These tables (budgets, manual expenses, macro→budget mapping) are owned by the
Streamlit app rather than by g_tracker's SQLAlchemy models, so they are created
here and every page calls init_schema() before it reads. Keeping it in one module
means the dashboard works even if you never open the Configuration page.
"""
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
# Absolute, so it no longer matters which directory streamlit was started from —
# financial_tracker/receipts.db is a stale leftover that must never be picked up.
DB_PATH = str(REPO_ROOT / "receipts.db")

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from taxonomy import (  # noqa: E402
    HOUSEHOLD_EQUIPMENT_MACRO,
    HOUSEHOLD_SUPPLIES_MACRO,
    SLOVAK_TAXONOMY,
    macro_categories,
)

GROCERIES = "groceries"
COSMETICS = "cosmetics"
HOUSEHOLD = "household"

# Reproduces the macro→budget CASE this used to hardcode, plus the new household line.
DEFAULT_MACRO_BUDGETS = {
    "Čerstvé potraviny": GROCERIES,
    "Trvanlivé potraviny": GROCERIES,
    "Nápoje": GROCERIES,
    "Mrazené potraviny": GROCERIES,
    "Pre zvieratá": GROCERIES,
    "Ostatné": GROCERIES,
    HOUSEHOLD_SUPPLIES_MACRO: COSMETICS,
    "Osobná hygiena a kozmetika": COSMETICS,
    "Zdravie a drogéria": COSMETICS,
    HOUSEHOLD_EQUIPMENT_MACRO: HOUSEHOLD,
}


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_schema(conn):
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
    )""")
    conn.execute("""
    -- Which budget line a scanned item's macro_category counts against.
    -- Data, not code: a new budget line no longer needs a SQL edit.
    CREATE TABLE IF NOT EXISTS category_mapping (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        person_id INTEGER NOT NULL,
        macro_category TEXT NOT NULL,
        category_id INTEGER NOT NULL,
        UNIQUE(person_id, macro_category),
        FOREIGN KEY (person_id) REFERENCES person (person_id),
        FOREIGN KEY (category_id) REFERENCES budget_categories (id) ON DELETE CASCADE
    )""")
    _ensure_is_goal_column(conn)
    conn.commit()


def _ensure_is_goal_column(conn):
    """A goal category fills up as you spend toward a monthly floor, instead of draining."""
    names = {row[1] for row in conn.execute("PRAGMA table_info(budget_categories)").fetchall()}
    if "is_goal" not in names:
        conn.execute("ALTER TABLE budget_categories ADD COLUMN is_goal BOOLEAN DEFAULT 0")


def get_category_id(conn, person_id, category_name):
    row = conn.execute(
        "SELECT id FROM budget_categories WHERE person_id = ? AND LOWER(category_name) = LOWER(?)",
        (person_id, category_name),
    ).fetchone()
    return row[0] if row else None


def seed_defaults(conn, person_id):
    """Create the household goal line and the initial macro→budget mapping.

    Both are one-shot: the mapping is only seeded when this person has none, so
    your later edits in the Configuration page are never overwritten.
    """
    if get_category_id(conn, person_id, HOUSEHOLD) is None:
        try:
            conn.execute(
                "INSERT INTO budget_categories (category_name, is_personal, monthly_limit, "
                "person_id, is_goal) VALUES (?, 0, 50.0, ?, 1)",
                (HOUSEHOLD, person_id),
            )
        except sqlite3.IntegrityError:
            # category_name is globally UNIQUE — someone else already owns the name.
            pass

    already_mapped = conn.execute(
        "SELECT COUNT(*) FROM category_mapping WHERE person_id = ?", (person_id,)
    ).fetchone()[0]
    if not already_mapped:
        for macro, budget_name in DEFAULT_MACRO_BUDGETS.items():
            category_id = get_category_id(conn, person_id, budget_name)
            if category_id is not None:
                conn.execute(
                    "INSERT OR IGNORE INTO category_mapping (person_id, macro_category, category_id) "
                    "VALUES (?, ?, ?)",
                    (person_id, macro, category_id),
                )
    conn.commit()
