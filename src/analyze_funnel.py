"""Read data/funnel.db and answer the four questions this project exists to ask.

  1. Where in the funnel do visitors actually drop out?
  2. Does the landing page a visitor arrives on change how far they get?
  3. How much of that difference is bot traffic rather than shopper intent?
  4. Which device and referrer carry the loss?

Every number here comes from SQL against the local database, not from the API.
"""
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "funnel.db"
REPORTS = PROJECT_ROOT / "reports"

# One row per dimension value, metrics summed across every date in the window.
BREAKDOWN = """
SELECT dimension_value,
       SUM(sessions)           AS sessions,
       SUM(cart_add_sessions)  AS cart_adds,
       SUM(checkout_sessions)  AS checkouts,
       SUM(completed_sessions) AS orders
FROM session_metrics_daily
WHERE dimension = ?
GROUP BY dimension_value
HAVING sessions > 0
ORDER BY sessions DESC
"""

TOTALS = """
SELECT SUM(sessions), SUM(cart_add_sessions),
       SUM(checkout_sessions), SUM(completed_sessions),
       MIN(date), MAX(date), COUNT(*)
FROM session_metrics_daily
WHERE dimension = 'day'
"""


def pct(numerator: int, denominator: int) -> str:
    """Format a share, without dividing by zero."""
    return f"{numerator / denominator * 100:5.2f}%" if denominator else "    --"


def table(rows: list[tuple], label: str, limit: int = 12) -> None:
    print(f"\n{label}")
    print(f"  {'value':<34}{'sess':>7}{'cart':>7}{'chk':>6}{'ord':>5}"
          f"{'cart%':>9}{'chk/cart':>10}{'conv%':>8}")
    for value, sessions, carts, checkouts, orders in rows[:limit]:
        print(f"  {str(value)[:33]:<34}{sessions:>7}{carts:>7}{checkouts:>6}{orders:>5}"
              f"{pct(carts, sessions):>9}{pct(checkouts, carts):>10}{pct(orders, sessions):>8}")


def funnel_chart(stages: list[tuple[str, int]]) -> Path | None:
    """Horizontal bar chart of the four stages. Skipped if matplotlib is absent."""
    try:
        import matplotlib
        matplotlib.use("Agg")  # no GUI window; write straight to a file
        import matplotlib.pyplot as plt
    except ImportError:
        print("\n(matplotlib not installed -- skipping chart)")
        return None

    REPORTS.mkdir(exist_ok=True)
    labels = [name for name, _ in stages][::-1]
    values = [count for _, count in stages][::-1]
    top = stages[0][1] or 1

    figure, axes = plt.subplots(figsize=(9, 4.5))
    bars = axes.barh(labels, values, color=["#c9a227", "#b08d57", "#8a7a5c", "#5c5240"])
    for bar, value in zip(bars, values):
        axes.text(bar.get_width() + top * 0.012, bar.get_y() + bar.get_height() / 2,
                  f"{value:,}  ({value / top * 100:.1f}%)", va="center", fontsize=10)
    axes.set_xlim(0, top * 1.28)
    axes.set_title("Pulse and Glow — 90-day session funnel", fontsize=13, pad=12)
    axes.set_xlabel("sessions")
    axes.spines[["top", "right"]].set_visible(False)
    figure.tight_layout()

    path = REPORTS / "funnel.png"
    figure.savefig(path, dpi=150)
    plt.close(figure)
    return path


def finding_chart(all_traffic: dict, humans: dict) -> Path | None:
    """The headline: cart-add rate by entry page, before and after removing bots."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return None

    REPORTS.mkdir(exist_ok=True)
    groups = ["Homepage", "Product"]
    series = [
        ("All traffic", [all_traffic.get(g, (0, 0)) for g in groups], "#b8b0a0"),
        ("Humans only", [humans.get(g, (0, 0)) for g in groups], "#c9a227"),
    ]

    figure, axes = plt.subplots(figsize=(8, 4.6))
    width, offsets = 0.36, (-0.18, 0.18)
    for (name, cells, color), offset in zip(series, offsets):
        rates = [cart / sess * 100 if sess else 0 for sess, cart in cells]
        positions = [i + offset for i in range(len(groups))]
        bars = axes.bar(positions, rates, width, label=name, color=color)
        for bar, rate, (sess, cart) in zip(bars, rates, cells):
            axes.text(bar.get_x() + bar.get_width() / 2, rate + 0.09,
                      f"{rate:.2f}%\n{cart}/{sess}", ha="center", fontsize=9)

    axes.set_xticks(range(len(groups)))
    axes.set_xticklabels([f"Landed on {g.lower()}" for g in groups])
    axes.set_ylabel("sessions that added to cart")
    axes.set_ylim(0, 4.9)
    axes.set_title("Entry page predicts cart-add — and bots do not explain it",
                   fontsize=13, pad=12)
    axes.legend(frameon=False)
    axes.spines[["top", "right"]].set_visible(False)
    figure.tight_layout()

    path = REPORTS / "finding_1.png"
    figure.savefig(path, dpi=150)
    plt.close(figure)
    return path


def main() -> None:
    connection = sqlite3.connect(DB_PATH)

    sessions, carts, checkouts, orders, first, last, days = connection.execute(TOTALS).fetchone()
    if not sessions:
        raise SystemExit("No rows for dimension 'day'. Run src/pull_sessions.py first.")

    print("=" * 78)
    print(f"PULSE AND GLOW FUNNEL — {first} to {last} ({days} days)")
    print("=" * 78)

    stages = [
        ("Sessions", sessions),
        ("Added to cart", carts),
        ("Reached checkout", checkouts),
        ("Completed order", orders),
    ]
    print("\nOverall funnel  (each stage counts SESSIONS IN WHICH the event occurred)")
    for name, count in stages:
        print(f"  {name:<20}{count:>7}   {pct(count, sessions)} of sessions")

    print("\n  These stages are NOT nested. A visitor can add to cart on Monday and")
    print("  check out on Thursday -- two sessions, two buckets, no link between them.")
    print("  So stage / previous-stage is not a conversion rate and can exceed 100%")
    print("  (see 'chk/cart' below). Only 'share of sessions' is safe to divide.")
    print(f"\n  The one drop that is safe to state: {sessions - carts} of {sessions} "
          f"sessions ({pct(sessions - carts, sessions)}) never added to cart.")

    for dimension, label in [
        ("landing_page_type", "By landing page type"),
        ("human_or_bot_session", "By human vs bot"),
        ("landing_page_type+human_or_bot_session",
         "CONFOUND TEST — landing page type x bot flag"),
        ("session_device_type", "By device"),
        ("referrer_source", "By referrer"),
        ("landing_page_path", "By landing page path (top 12)"),
    ]:
        rows = connection.execute(BREAKDOWN, (dimension,)).fetchall()
        if rows:
            table(rows, label)
        else:
            print(f"\n{label}\n  (no rows stored for '{dimension}')")

    # Human-only funnel: the honest version of Finding 1.
    human = connection.execute(BREAKDOWN, ("landing_page_type+human_or_bot_session",)).fetchall()
    human_rows = [r for r in human if "human" in str(r[0]).lower()]
    if human_rows:
        print("\nHuman-only cart-add rate by landing page type")
        for value, sess, cart, _chk, _ord in sorted(human_rows, key=lambda r: -r[1]):
            print(f"  {str(value)[:40]:<42}{sess:>7} sessions   cart-add {pct(cart, sess)}")

    # Is the human-only homepage/product gap bigger than chance? One-tailed
    # Fisher exact test -- no scipy, just the hypergeometric tail by hand.
    cells = {str(v).lower(): (sess, cart) for v, sess, cart, _c, _o in human}
    home = cells.get("homepage | human")
    prod = cells.get("product | human")
    if home and prod:
        from math import comb
        a, b = home[1], home[0] - home[1]          # homepage: adds, no-adds
        c, d = prod[1], prod[0] - prod[1]          # product:  adds, no-adds
        adds, total, prod_n = a + c, home[0] + prod[0], prod[0]
        # P(product sees <= c adds) given the margins.
        p_value = sum(
            comb(adds, k) * comb(total - adds, prod_n - k) / comb(total, prod_n)
            for k in range(0, c + 1)
        )
        print("\nSignificance of the human-only gap (one-tailed Fisher exact)")
        print(f"  homepage humans : {a:>4} cart-adds / {home[0]:>4} sessions  {pct(a, home[0])}")
        print(f"  product  humans : {c:>4} cart-adds / {prod[0]:>4} sessions  {pct(c, prod[0])}")
        print(f"  p = {p_value:.5f}  ->  "
              f"{'not chance' if p_value < 0.05 else 'cannot rule out chance'}")

    for path in (
        funnel_chart(stages),
        finding_chart(
            {str(v): (s_, c) for v, s_, c, _k, _o in
             connection.execute(BREAKDOWN, ("landing_page_type",)).fetchall()},
            {str(v).split(" | ")[0]: (s_, c) for v, s_, c, _k, _o in human_rows},
        ),
    ):
        if path:
            print(f"chart written to {path.relative_to(PROJECT_ROOT)}")

    connection.close()


if __name__ == "__main__":
    main()
