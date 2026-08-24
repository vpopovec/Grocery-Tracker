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

### Item-level transaction lookup

Answer questions like *"what did I actually buy for the household this month?"* — today nothing
can. The Transaction Browser
([2_Transaction_Browser.py](financial_tracker/pages/2_Transaction_Browser.py)) aggregates one row
per shopping trip: item names are flattened into a `GROUP_CONCAT` "Details" string, and the row's
`Category` is `COALESCE(LOWER(i.macro_category), 'groceries')` — whichever item SQLite happened to
pick out of the group, which is arbitrary and often wrong for a mixed receipt.

So a €63 IKEA trip shows as one row, and filtering by category can't reach the individual lamp or
carpet inside a mixed Kaufland receipt.

- Add an item-level view (or a toggle on the existing one) that lists individual items with their
  date, shop, macro/micro category and price, instead of one row per receipt.
- Filter by macro *and* micro, and by budget line via `category_mapping` — "show me everything
  routed to household in this cycle" is the driving question.
- Default the date range to the current budget cycle (`get_current_cycle_start` in
  [streamlit_app.py](financial_tracker/streamlit_app.py)) so it lines up with what the dashboard
  bar is showing; make it easy to widen to "last 6 months" for a trend.
- Show the running total for the current filter, so clicking through from the Household goal bar
  reconciles against the number on the dashboard.
- Drop the arbitrary-category bug above while you are in there: a receipt spanning several macros
  should not claim a single one.

### Register a new shop

`shop_name` is normalized against a fixed whitelist that lives in the model prompt
([taxonomy.py](taxonomy.py) `SHOP_NAMES`, injected into both prompts in [main.py](main.py)).
Anything not on the list becomes `"Unknown"`. Household equipment made this concrete — IKEA, Jysk,
Möbelix, Alza, Datart, OBI and Hornbach had to be added by hand. Let the user add a shop from the
UI instead, persisted per person and injected into the prompt at scan time.

---

## Deferred

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
