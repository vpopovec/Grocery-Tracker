# Active Work — Financial Tracker

## 1. Household Category

Goal: see at a glance, every month, whether something went into the household — a lamp, a blender,
a carpet. This is a **floor to reach, not a ceiling to stay under**. Everything previously in this
file moved to [BACKLOG.md](BACKLOG.md).

Status: **implemented**. What follows is the shape of the change and how to check it.

---

### The problem it solved

`SLOVAK_TAXONOMY` had a macro called **"Domácnosť"**, but it meant *consumables* — cleaning
products, paper towels, bags, candles. Durable goods had nowhere to go except
`Ostatné → Nezaradené`. Macro → budget routing was a hardcoded SQL `CASE` in the Streamlit
dashboard, and after a scan there was no way to correct an item's category at all.

### What changed

**Taxonomy** — moved out of `main.py` into a stdlib-only [`taxonomy.py`](taxonomy.py) at the repo
root, so the Flask app and the out-of-process Streamlit tracker share one definition.

- The consumables macro was renamed **"Drogéria a domáce potreby"** (still routed to `cosmetics`).
- **"Domácnosť"** now means durable equipment: `Nábytok`, `Osvetlenie`, `Kuchynské spotrebiče`,
  `Veľké spotrebiče`, `Riad a kuchynské potreby`, `Bytový textil a doplnky`,
  `Náradie a železiarstvo`, `Záhrada a rastliny`, `Elektronika a domáca technika`.
- `ensure_household_taxonomy_rename` in [`sqlite_db.py`](sqlite_db.py) retagged the 28 existing
  rows. It filters on the old micro names, so it is permanently safe to re-run.
- Both scan prompts gained an explicit consumable-vs-durable rule, and the shop whitelist grew
  IKEA, Jysk, Möbelix, Alza, Datart, OBI and Hornbach — household receipts were all normalizing to
  `"Unknown"`.

**Routing is data now, not code** — a `category_mapping` table (`person_id`, `macro_category`,
`category_id`) replaces the `CASE`. Unmapped macros still fall back to `groceries`. Editable under
*Route Scanned Items to Budget Lines* on the Configuration page; the row list is driven by the
taxonomy, so a macro added to `taxonomy.py` appears there automatically.

**The Household line is a goal, not a cap** — `budget_categories.is_goal` inverts the bar: it fills
as you spend (blue), turns green at 100%, and reads `64 € invested / 50 € goal` with a 🎯 next to
the name. Seeded at €50, editable in the Configuration editor.

**Per-item correction** — the `/items` grid gained Category and Subcategory dropdowns. The
subcategory list follows the chosen macro, both fields save together, and the server rejects a
micro that doesn't belong to its macro. The taxonomy is injected server-side rather than fetched,
so nothing races the grid's first render, and the `change` listener is delegated on the table
because grid.js re-renders on sort/search/paginate.

### Fixes carried along

- **Quantities were double-counted.** The rollup multiplied `i.price * COALESCE(i.amount, 1)`, but
  `price` is already the line total written by `sqlite_db.save_receipt` — 4 yogurts at €2.12 counted
  as €8.48. Across all history this inflated groceries by **€706 (~27%)**.
- **A NULL `monthly_limit` crashed `/analytics`** via an unguarded `float(...)`. Such lines now
  render as spend-only, no bar.
- **`POST /api/data` and `/delete-row` trusted a client-supplied `item_id`**, so any logged-in user
  could edit or delete another user's item by guessing. Both now resolve items through
  `get_owned_item()` and 404 otherwise.
- **Configuration page was not person-scoped**: it read every user's categories, wrote
  `person_id = 1` on save, and its `DELETE ... WHERE id NOT IN (...)` would have wiped other users'
  rows. All three now use the authenticated `user_id`.
- **`uv run pytest tests/` was deleting the production database.** The fixture in
  `tests/test_llm_quota.py` called `create_app()` and *then* set
  `SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'` — but Flask-SQLAlchemy binds its engine during
  `init_app`, so the override came too late and the fixture's `db.drop_all()` teardown emptied the
  real `receipts.db`. (Hit during this work; restored from a backup.) The fixture now passes a
  `TestConfig` *into* `create_app` and asserts it isn't pointed at `receipts.db`. `_ensure_sqlite_schema`
  also skips `:memory:` and no-ops on a database with no `receipt` table — which is what the two
  long-standing test errors actually were.
- **`DB_PATH` was the relative `"../receipts.db"`**, one wrong working directory away from
  migrating the stale 20 KB `financial_tracker/receipts.db`. It is now resolved absolutely from
  `__file__` in [`financial_tracker/schema.py`](financial_tracker/schema.py), which also owns all
  the tracker's `CREATE TABLE`s and the one-shot seeding.

### Files

| File | Change |
|---|---|
| [`taxonomy.py`](taxonomy.py) *(new)* | Shared taxonomy, shop list, validation helpers |
| [`financial_tracker/schema.py`](financial_tracker/schema.py) *(new)* | Connection, table creation, default mapping seed |
| [`main.py`](main.py) | Imports the taxonomy; prompt rules; shop whitelist |
| [`sqlite_db.py`](sqlite_db.py) | `ensure_household_taxonomy_rename` backfill |
| [`g_tracker/item_table.py`](g_tracker/item_table.py) | Category fields, pair validation, ownership checks |
| [`g_tracker/templates/item_table.html`](g_tracker/templates/item_table.html) | Dropdown columns, delegated change handler, upload button |
| [`financial_tracker/streamlit_app.py`](financial_tracker/streamlit_app.py) | Mapping-driven rollup, count fix, goal bar |
| [`financial_tracker/pages/1_Configuration.py`](financial_tracker/pages/1_Configuration.py) | `is_goal`, routing editor, person scoping |
| [`g_tracker/__init__.py`](g_tracker/__init__.py) | Migrations skip `:memory:` / empty databases |
| [`tests/test_llm_quota.py`](tests/test_llm_quota.py) | Fixture no longer binds to the real DB |

---

### Verification

```bash
# 1. Backfill ran and is idempotent (second run prints nothing, counts unchanged)
uv run flask run --port=5000
sqlite3 receipts.db "SELECT macro_category, COUNT(*) FROM item GROUP BY 1 ORDER BY 2 DESC"

# 2. Dashboard — run from financial_tracker/ (or anywhere; DB_PATH is absolute now)
cd financial_tracker && uv run streamlit run streamlit_app.py
```

- `/items` — set a row to `Domácnosť → Osvetlenie` and reload; it sticks. Changing the macro
  repopulates the subcategory list.
- `/analytics` — the Household line shows 🎯, fills as you add household items, turns green at the
  goal. Remap `Nápoje` to `cosmetics` on the Configuration page and watch the money move.
- Scan a receipt containing a durable item and confirm the model files it under `Domácnosť`. If it
  lands in `Ostatné`, tighten the prompt rule rather than adding keyword hacks.
- `uv run pytest tests/` — 3 passed. Confirm `SELECT COUNT(*) FROM receipt` is unchanged before and
  after: this suite used to wipe the real database, and the fixture assertion now guards it.

**Back up `receipts.db` before running anything destructive.** It is gitignored, so git will not
save you.

---

## 2. Quick "Upload" navigation

Status: **implemented**.

Scanning several receipts in a row meant going back up to the navbar every time. The flow is
upload → scan → land on `/items` to check the extraction → and then nothing points at the next
upload.

- **`/items`** gained an `⬆️ Upload Next Receipt` button below the total. This is the important
  one: it is where [receipts.py](g_tracker/receipts.py) redirects after a successful scan, so it
  closes the loop right where you finish reviewing.
- **`/receipts`** gained an `⬆️ Upload Receipt` button below the table, for starting from the list.

Both are plain links to `url_for('receipt.index')` (`/scan`) styled `btn btn-primary btn-lg` — the
primary action on the page, unlike the outline-secondary buttons next to them.

### Verification

Open `/items` and `/receipts`, click the button, confirm it lands on the upload form. After a scan
completes you should be able to go straight into the next one without touching the navbar.
