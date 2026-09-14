# pulse-glow-funnel-analysis

Diagnosing where visitors drop out of a live Shopify store's conversion funnel.

**90 days (2026-06-16 → 2026-09-14) · 1,638 sessions · 23 cart additions · 2 orders.**
Python · ShopifyQL (Admin GraphQL API) · SQLite · SQL · matplotlib

## The finding

**98.6% of sessions never add an item to the cart.** The break is not at checkout —
it is before a visitor engages with a product at all.

The page a visitor lands on predicts whether they ever add to cart. Device and
referrer do not.

| Landed on | Sessions | Cart adds | Rate |
|---|---|---|---|
| Homepage | 757 | 22 | **2.91%** |
| Product page | 750 | 1 | **0.13%** |

Shopify labels **72% of this store's traffic as bot** (1,184 of 1,638), so the
headline was re-tested on human sessions only:

| Landed on (humans only) | Sessions | Cart adds | Rate |
|---|---|---|---|
| Homepage | 286 | 11 | **3.85%** |
| Product page | 152 | 0 | **0.00%** |

One-tailed Fisher exact test: **p = 0.0086.** The gap is not bot traffic and is
not chance. The single product-page cart addition in the whole window came from a
session Shopify flagged as a bot.

## A constraint that shapes everything here

The four metrics count *sessions in which an event occurred*, independently of one
another — they are not a nested cohort. Broken out by referrer, `direct` shows 15
cart-add sessions but 18 checkout-reaching sessions. **Stage-to-stage division is
therefore meaningless and can exceed 100%.** Only "share of all sessions" is a
safe ratio. The schema is an aggregate fact table for that reason, not a funnel.

## Running it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # add SHOPIFY_STORE, SHOPIFY_CLIENT_ID, SHOPIFY_CLIENT_SECRET
python src/pull_sessions.py     # API -> SQLite
python src/analyze_funnel.py    # SQLite -> findings + reports/funnel.png
```

| File | Does |
|---|---|
| `src/shopify_client.py` | Exchanges client credentials for a 24-hour Admin API token |
| `src/check_env.py` | Confirms credentials load without printing them |
| `src/pull_sessions.py` | Seven ShopifyQL queries → upsert into `data/funnel.db` |
| `src/analyze_funnel.py` | SQL over the database → funnel, breakdowns, significance test, chart |
| `sql/schema.sql` | `session_metrics_daily`, keyed on (date, dimension, dimension_value) |
| `sql/analysis.sql` | The five queries behind the findings |

## Notes on the API

- ShopifyQL is **not SQL**. Metrics are already aggregates — `SHOW` names which
  totals you want; there is no `sum()` to apply.
- Grouping is **`GROUP BY`**, not `BY`. A bare `BY` is rejected by the parser.
- `shopifyqlQuery` requires Admin API version **2025-10 or higher** and the
  **`read_reports`** scope. No Protected Customer Data approval was needed for a
  custom app inside the same Shopify organization as the store.
- Tokens expire in 86,399 seconds, so every run exchanges credentials afresh
  rather than caching.
