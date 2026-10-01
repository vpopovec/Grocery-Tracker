# Backlog

Ideas parked from earlier plans, plus new ones. Nothing here is scheduled — active work lives in
[PLAN.md](PLAN.md). Entries keep their original detail (file:line references, concrete bugs) so
they can be picked up without re-deriving the context.

---

## Done

### Lock down `/analytics` ✅

Implemented via Caddy `forward_auth` gating `/analytics*` against a Flask
`/internal/verify-session` endpoint, which copies `X-Person-Id` upstream to Streamlit
(replacing the hardcoded `person_id = 1` in all three Streamlit pages). Fixed one bug along the
way: Werkzeug's dev server 400'd on the WebSocket `Upgrade`/`Connection` headers Caddy forwarded
into the auth sub-request — resolved by clearing those headers specifically on the `forward_auth`
call. Verified from a logged-out browser. Flask (:5000) and Streamlit (:8501) were already bound
to 127.0.0.1 only; Caddy is the sole public entry point.

### Item-level transaction lookup ✅

`2_Transaction_Browser.py` now carries a **By receipt / By item** toggle. The item view lists every
scanned line with its own date, shop, macro, micro, budget line and price, unions in manual expenses
as single rows (so totals match the dashboard, which counts both sources), and filters by budget
line — plus macro, with the micro dropdown narrowing to the chosen macro. Date range defaults to the
active cycle with presets out to all-time.

The arbitrary-category bug is gone: the old query selected `i.macro_category` while grouping by
receipt, so SQLite picked one item's category for the whole trip. A receipt spanning several budget
lines now reads **Mixed**, and filtering by a line matches any receipt *containing* it, so a mixed
Kaufland trip still surfaces under household instead of vanishing.

Cycle helpers moved out of `streamlit_app.py` into `financial_tracker/cycle.py` — importing that
module to get the cycle would have re-run the entire dashboard UI. Verified every budget line's
item-view total against `get_budget_status()` for the current cycle: all reconcile.

### Delete transactions from the ledger ✅

Split by ownership. **Manual expenses** are deleted in Streamlit (owner-scoped
`DELETE ... WHERE expense_id = ? AND person_id = ?`) — Streamlit is the only writer of
`manual_expenses`, so there is nothing else to clean up. **Scanned receipts** are not deleted from
Streamlit: a receipt is items *plus* a `scan` row *plus* an image on disk *plus* the `RECEIPT_ID`
focus pointer, and `item_table.delete_receipt` is the only place that knows all four. The ledger
links out instead — `/receipts?focus=<id>` (new, owner-scoped) pulls that receipt into a card above
the grid with its own delete button, so the deep link lands on the receipt you clicked.

Selecting a row in either view opens an action panel: delete-with-confirmation for a manual expense,
a link to the Receipt Manager for a scanned one.

### `item.receipt_id` foreign key pointed at a non-existent table ✅

[receipts_schema.sql:22](receipts_schema.sql:22) declared `REFERENCES receipts (receipt_id)` —
plural, a table that has never existed. Under `PRAGMA foreign_keys = ON` (which
`financial_tracker/schema.py` sets on every connection) any delete touching `item` died with
`no such table: main.receipts`. Nothing hit it because Flask/SQLAlchemy runs with FKs *off* and
Streamlit had never deleted anything. `models.py` already had it right; only the raw DDL was wrong.

Fixed in the schema file and migrated in the live DB by rebuilding the table (SQLite cannot `ALTER`
a constraint), dropping and restoring the `remove_items` trigger around the swap, which otherwise
blocks the drop. 1833 rows / €3378.61 identical before and after; `integrity_check` ok. Backup at
`receipts.db.bak-20260826-000209`.

### Household category ✅

Macro/micro editing on `/items`, a data-driven `category_mapping` table replacing the hardcoded
macro→budget `CASE`, and the household goal line. See [PLAN.md](PLAN.md).

---

## Ideas — still worth doing

### Rewrite Receipt Buddy as a real tool-use loop

`ai_financial_agent()` at [insight.py:240](g_tracker/insight.py:240) is not an agent: it runs one
fixed SQL aggregate, renders the *entire* monthly × macro × micro breakdown into a markdown table
in the system prompt, and makes a single Groq call. Every question pays for the whole dataset, and
the model can never ask a question the one hardcoded query didn't anticipate.

- Define 3–4 **narrow** tools rather than one `run_sql` escape hatch:
  `get_spending_by_category(start_date, end_date, macro_category=None)`,
  `get_receipts(start_date, end_date, shop_name=None, limit=...)`,
  `get_monthly_totals(months_back)`, `search_items(name_substring, limit)`.
- Enforce `person_id` scoping **inside** each tool implementation, taken from `current_user`.
  It must never be a model-supplied parameter, or one user can read another's data by asking nicely.
- Implement the loop: call → if `stop_reason` is tool use, execute, append the result, call again →
  repeat under a hard iteration cap (5 is plenty here).
- Cap tool result sizes (row limits, rounded currency) so a broad date range can't blow up context.
- Route it through the existing `INSIGHT_CHAT` quota in [llm_quota.py](g_tracker/llm_quota.py) —
  one *conversation* should consume one unit, not one unit per tool round-trip.

### Verification pass on receipt extraction

`Receipt.total` at [main.py:291](main.py:291) is the **sum of items**, while the model's extracted
`total_amount` is parsed into `ReceiptData` and then never compared against it. The prompt asks the
model to self-check its own math — an unverified self-report.
[IMPROVE_PROMPT.md](IMPROVE_PROMPT.md) records this plus the fact that the fast Qwen config mangles
discounts (IMG_1709).

- Add a programmatic check: `abs(sum(items) - total_amount) > 0.01` → mismatch.
- On mismatch, re-prompt once with the discrepancy stated explicitly ("your items sum to X but you
  reported total Y; look again for missed discount lines or multi-quantity rows") rather than
  blindly retrying the same prompt.
- If the second pass still disagrees, surface it to the user — this is where the "Take a photo with
  less glare" message belongs. Fail loudly instead of silently persisting a wrong total.
- Persist the mismatch delta so you can see how often pass 2 rescues pass 1.
- Re-test against the known-bad receipts in `receipts/`, IMG_1709 included.

### MCP server over the receipts DB

Reuse the tool implementations from the tool-use loop above — same functions, different transport.

- Stand up a minimal MCP server exposing the read-only query tools.
- Write real tool descriptions and JSON schemas by hand; note where an ambiguous description makes
  the model pick the wrong tool.
- Keep it read-only. A write tool would need an authorization story that doesn't exist yet.

### Multi-receipt upload

The current flow assumes one file and immediately redirects to the validation screen
([receipts.py:206](g_tracker/receipts.py:206)); batching needs a queue/review UI. Isolate per-file
failures so one bad image doesn't fail the batch. Pairs naturally with the quick-upload nav below.

### Register a new shop — done

Per-user `person_shop` rows plus defaults from `SHOP_NAMES`. After a scan lands as
`Unknown`, `/scan/register-shop/<id>` prompts with the LLM `shop_name_guess` prefilled.
Confirmed names are normalized (case-insensitive dedupe), saved for that person, applied
to the current receipt only, and injected into the next scan prompt.


---

## Deferred

- **16 orphaned `scan` rows** point at receipts that no longer exist, with their image files still
  in `receipts/`. Not from deletes — `receipt` carries
  `UNIQUE(person_id, shop_name, shopping_date, total) ON CONFLICT REPLACE`, so re-scanning the same
  receipt replaces the row under a new `receipt_id` and strands the old scan (the "not on replace,
  leider" comment on [models.py:18](g_tracker/models.py:18) is about this). `PRAGMA foreign_key_check`
  lists them. Decide whether the fix is cleaning them up, an `ON DELETE CASCADE`, or dropping the
  REPLACE behaviour — each also has to say what happens to the image file.
- **Mobile-friendly UI / narrower tables.** The `/items` grid now carries two more columns; the
  category dropdowns are capped at `11rem` but the table is still wide on a phone.
- **General refactoring.**
- **Multi-tenant onboarding flow** (first-visit budget category setup).
- **`budget_categories.category_name` is globally `UNIQUE`**, so two people can't both have a
  "groceries" line. Needs to become `UNIQUE(person_id, category_name)`; `schema.seed_defaults`
  currently swallows the resulting `IntegrityError`.
- **`RECEIPT_ID` lives in `current_app.config`** ([item_table.py:155](g_tracker/item_table.py:155)),
  i.e. it is global to the process rather than per-session — two users editing at once would see
  each other's receipt. `GET /api/data` inherits this: it filters by that global id, not by owner.
  (`POST /api/data` and `/delete-row` are now owner-scoped.)
