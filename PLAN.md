# CCA-F Prep Plan — Grocery / Financial Tracker

Using this codebase as a practice vehicle for the **Claude Certified Architect — Foundations** exam
(60 questions / 120 min, pass 720/1000, proctored, closed-book). Target: ~mid-August 2026.

**Exam domains and weights:**

| Domain | Weight |
|---|---|
| Agentic Architecture & Orchestration | 27% |
| Claude Code Configuration & Workflows | 20% |
| Prompt Engineering | 20% |
| Tool Design & MCP | 18% |
| Context Management | 15% |

**Ground rule for the next two weeks:** the exam is closed-book and conceptual. Building teaches
intuition that multiple-choice questions reward, but it is not a substitute for studying. Budget
roughly 60% reading/mock exams, 40% the tasks below. If time runs short, tasks are ordered so that
stopping after Task 2 still covers the two heaviest domains.

---

## Task 0 — Lock down `/analytics` (do first, not exam-related)

The Streamlit financial tracker is on a public Azure VM with an unauthenticated `/analytics`
endpoint, and `get_current_user_id()` in [streamlit_app.py](financial_tracker/streamlit_app.py:52)
assumes a single owner. This is a live exposure. It earns zero exam points — do it anyway, this
week, and timebox it.

- [ ] Decide the auth approach (Streamlit native auth vs. reverse-proxy basic auth on the VM vs.
      shared-secret query gate). Proxy-level is likely fastest and least code.
- [ ] Confirm nothing else on the VM is unintentionally listening (`ss -tlnp`, check the Flask app's
      bind address too).
- [ ] Make `get_current_user_id()` derive from the authenticated session rather than returning a
      hardcoded/implicit owner.
- [ ] Verify from a logged-out browser / incognito that `/analytics` refuses access.

Multi-tenant onboarding (first-visit budget category setup) is deliberately **not** in scope here —
it is a product feature, not a security fix, and it is not exam-relevant. Separate it out.

---

## Task 1 — Rewrite Receipt Buddy as a real tool-use loop  *(27% + 18% + 15%)*

**Highest exam value of anything in this repo.** `ai_financial_agent()` at
[insight.py:240](g_tracker/insight.py:240) is not an agent: it runs one fixed SQL aggregate, renders
the *entire* monthly × macro × micro breakdown into a markdown table in the system prompt, and makes
a single Groq call. Every question pays for the whole dataset, and the model can never ask a
question the one hardcoded query didn't anticipate.

Converting it to a tool-use loop exercises the agentic loop (gather context → act → verify), tool
design, and context management simultaneously.

- [ ] Define 3–4 **narrow** tools rather than one `run_sql` escape hatch. Candidate set:
      `get_spending_by_category(start_date, end_date, macro_category=None)`,
      `get_receipts(start_date, end_date, shop_name=None, limit=...)`,
      `get_monthly_totals(months_back)`, `search_items(name_substring, limit)`.
      Writing these schemas by hand is the point — do not skip to a generic query tool.
- [ ] Enforce `person_id` scoping **inside** each tool implementation, taken from
      `current_user`. It must never be a model-supplied parameter, or one user can read another's
      data by asking nicely.
- [ ] Implement the agentic loop: call → if `stop_reason` is tool use, execute, append the result,
      call again → repeat under a hard iteration cap (5 is plenty here).
- [ ] Cap tool result sizes (row limits, rounded currency) so a broad date range can't blow up the
      context window. Note what you had to truncate — that instinct is the 15% domain.
- [ ] Port to the Anthropic SDK. Currently this path is Groq/llama and the receipt path is Gemini
      via OpenRouter; the exam tests Anthropic's API surface, so hands-on here pays off directly.
      Keep the Groq version behind a config flag if cost matters.
- [ ] Route it through the existing `INSIGHT_CHAT` quota in
      [llm_quota.py](g_tracker/llm_quota.py) — one *conversation* should consume one unit, not one
      unit per tool round-trip.
- [ ] Write down, in a comment or here, how the token cost per question compares before vs. after.

**Study hook:** after building this, you should be able to explain *without notes* why narrow typed
tools beat a generic SQL tool, and when prompt-stuffing is actually the better choice.

---

## Task 2 — Verification pass on receipt extraction  *(27% agentic loop, "verify results")*

Concrete bug backing this: `Receipt.total` at [main.py:291](main.py:291) is the **sum of items**,
while the model's extracted `total_amount` is parsed into `ReceiptData` and then never compared
against it. The prompt at [main.py:151](main.py:151) asks the model to self-check its own math —
which is exactly the kind of unverified self-report the exam wants you to distrust.
[IMPROVE_PROMPT.md](IMPROVE_PROMPT.md) already records both this idea and that the fast Qwen config
mangles discounts (IMG_1709).

- [ ] Add a programmatic check: `abs(sum(items) - total_amount) > 0.01` → mismatch.
- [ ] On mismatch, re-prompt once with the discrepancy stated explicitly ("your items sum to X but
      you reported total Y; look again for missed discount lines or multi-quantity rows") rather
      than blindly retrying the same prompt.
- [ ] If the second pass still disagrees, surface it to the user — this is where the
      "Take a photo with less glare" message from IMPROVE_PROMPT.md belongs. Fail loudly instead of
      silently persisting a wrong total.
- [ ] Persist the mismatch delta so you can see how often pass 2 rescues pass 1.
- [ ] Re-test against the known-bad receipts in `receipts/`, IMG_1709 included.

**Study hook:** this is the difference between a model *claiming* it verified and a system that
*checks*. Expect exam questions in this shape.

---

## Task 3 — MCP server over the receipts DB  *(18%)*

Reuse the tool implementations from Task 1 — same functions, different transport. Doing both is what
teaches the distinction between a tool the app calls in a loop and a tool exposed over MCP.

- [ ] Stand up a minimal MCP server exposing the read-only query tools.
- [ ] Write real tool descriptions and JSON schemas by hand; note where an ambiguous description
      causes the model to pick the wrong tool. That failure is the lesson.
- [ ] Keep it read-only for now. A write tool would need an authorization story you don't have yet.
- [ ] Connect it to Claude Code (or the desktop app) and ask questions about your actual spending.
- [ ] Understand the transport options (stdio vs. HTTP) well enough to explain when each applies —
      this shows up on the exam.

---

## Task 4 — Multi-receipt upload, as a Claude Code workflow exercise  *(20%)*

The feature itself carries little exam weight. Its value is as a **vehicle** for practicing the
Claude Code Workflows domain, so run it deliberately rather than just asking for the feature.

- [ ] Write a `CLAUDE.md` for this repo first. There is real context scattered across
      [IMPROVEMENTS.md](IMPROVEMENTS.md), [notes.txt](notes.txt),
      [notes_personal.md](notes_personal.md), and [CHANGES_APPLIED.md](CHANGES_APPLIED.md) that
      should be consolidated where Claude will actually load it.
- [ ] Use plan mode to design the batch flow before any code is written. Current flow assumes one
      file and immediately redirects to the validation screen
      ([receipts.py:206](g_tracker/receipts.py:206)) — batching needs a queue/review UI.
- [ ] Try a subagent for an isolated slice and observe what context it lacks. Noticing what a fresh
      agent *doesn't* know is the core intuition this domain tests.
- [ ] Note where per-file failures should be isolated so one bad image doesn't fail the batch.
- [ ] Afterwards, write 3–5 sentences on which workflow tools helped and which were overhead.
      Honest negative results are more useful for the exam than a clean success story.

---

## Explicitly deprioritized

Not because they're bad ideas — because they carry ~0% exam weight and you have two weeks.

- **Mobile-friendly UI / narrower tables.** Pure frontend. Revisit after the exam.
- **General refactoring.** You already flagged "maybe not now." Agreed.
- **Multi-tenant onboarding flow** (first-visit budget category setup). Real product value, no exam
  overlap. Separate from the Task 0 security fix, which does need doing now.

---

## Suggested sequencing

| | Focus |
|---|---|
| **Week 1** | Task 0 (timeboxed), then Task 1. Study alongside: agentic loop patterns, tool design, context management. |
| **Week 2** | Task 2, then Task 3 if time allows. Shift the balance toward mock exams as the date approaches. |
| **If short on time** | Stop after Task 2. Tasks 1 + 2 cover the 27% and much of 18% + 15% — the heaviest material. |
| **After the exam** | Task 4, mobile UI, onboarding, refactor. |

Cross-check the domain weights against the official exam guide before relying on this ordering —
they come from third-party write-ups, not Anthropic's own published outline.
