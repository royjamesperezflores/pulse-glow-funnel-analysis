"""Re-derive Findings 2 and 3 from the database instead of from the API.

Finding 2 — the Meta ad flight (Jul 30 - Aug 21) bought the window's biggest
            traffic days and produced almost no cart additions.
Finding 3 — cart additions are violently lumpy: a couple of days carry most of
            the 90-day total, which is why no before/after test can work here.

Both were originally measured through Claude's connector in Session 1. Nothing
here touches the network -- it is SQL over data/funnel.db.
"""
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "funnel.db"
REPORTS = PROJECT_ROOT / "reports"

AD_FLIGHT_START, AD_FLIGHT_END = "2026-07-30", "2026-08-21"

DAILY = """
SELECT date, sessions, cart_add_sessions, completed_sessions
FROM session_metrics_daily
WHERE dimension = 'day'
ORDER BY date
"""

# Same series, humans only -- the bot split was not available in Session 1.
DAILY_HUMAN = """
SELECT date, SUM(sessions), SUM(cart_add_sessions)
FROM session_metrics_daily
WHERE dimension = 'human_or_bot_session'
  AND LOWER(dimension_value) LIKE '%human%'
GROUP BY date
ORDER BY date
"""


def pct(a: int, b: int) -> str:
    return f"{a / b * 100:.2f}%" if b else "--"


def main() -> None:
    connection = sqlite3.connect(DB_PATH)
    days = connection.execute(DAILY).fetchall()
    human_days = connection.execute(DAILY_HUMAN).fetchall()

    total_sessions = sum(d[1] for d in days)
    total_carts = sum(d[2] for d in days)

    print("=" * 74)
    print(f"DAILY SERIES — {days[0][0]} to {days[-1][0]}  ({len(days)} days)")
    print("=" * 74)

    print("\nFINDING 3 — how concentrated are the cart additions?")
    by_carts = sorted(days, key=lambda d: -d[2])
    print(f"  {'date':<13}{'sessions':>9}{'cart adds':>11}{'cart%':>9}")
    for date, sessions, carts, _orders in by_carts[:6]:
        print(f"  {date:<13}{sessions:>9}{carts:>11}{pct(carts, sessions):>9}")
    top2 = sum(d[2] for d in by_carts[:2])
    zero_days = sum(1 for d in days if d[2] == 0)
    print(f"\n  Top 2 days carry {top2} of {total_carts} cart adds "
          f"({pct(top2, total_carts)} of the 90-day total).")
    print(f"  {zero_days} of {len(days)} days ({pct(zero_days, len(days))}) had ZERO cart adds.")
    print("  -> Day-to-day variance swamps any plausible effect size. A before/after")
    print("     test cannot separate a real lift from two good days landing on one side.")

    print("\nFINDING 2 — the Meta ad flight (Jul 30 - Aug 21)")
    by_sessions = sorted(days, key=lambda d: -d[1])
    print("  Busiest days in the window:")
    print(f"  {'date':<13}{'sessions':>9}{'cart adds':>11}{'orders':>8}")
    for date, sessions, carts, orders in by_sessions[:5]:
        flag = "  <- in ad flight" if AD_FLIGHT_START <= date <= AD_FLIGHT_END else ""
        print(f"  {date:<13}{sessions:>9}{carts:>11}{orders:>8}{flag}")

    flight = [d for d in days if AD_FLIGHT_START <= d[0] <= AD_FLIGHT_END]
    rest = [d for d in days if not (AD_FLIGHT_START <= d[0] <= AD_FLIGHT_END)]
    print(f"\n  {'period':<22}{'days':>6}{'sessions':>10}{'cart adds':>11}{'cart-add rate':>15}")
    for label, group in (("ad flight", flight), ("rest of window", rest)):
        s = sum(d[1] for d in group)
        c = sum(d[2] for d in group)
        print(f"  {label:<22}{len(group):>6}{s:>10}{c:>11}{pct(c, s):>15}")

    print("\n  Humans only, same split (not available in Session 1):")
    hflight = [d for d in human_days if AD_FLIGHT_START <= d[0] <= AD_FLIGHT_END]
    hrest = [d for d in human_days if not (AD_FLIGHT_START <= d[0] <= AD_FLIGHT_END)]
    for label, group in (("ad flight", hflight), ("rest of window", hrest)):
        s = sum(d[1] for d in group)
        c = sum(d[2] for d in group)
        print(f"  {label:<22}{len(group):>6}{s:>10}{c:>11}{pct(c, s):>15}")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("\n(matplotlib missing -- no chart)")
        return

    REPORTS.mkdir(exist_ok=True)
    dates = [d[0] for d in days]
    figure, axes = plt.subplots(figsize=(11, 4.4))
    axes.fill_between(range(len(days)), [d[1] for d in days],
                      color="#d8d2c4", label="sessions")
    axes.bar(range(len(days)), [d[2] * 20 for d in days],
             color="#c9a227", width=0.8, label="cart adds (x20 for visibility)")
    start = next((i for i, d in enumerate(dates) if d >= AD_FLIGHT_START), None)
    stop = next((i for i, d in enumerate(dates) if d > AD_FLIGHT_END), len(days) - 1)
    if start is not None:
        axes.axvspan(start, stop, color="#8a7a5c", alpha=0.16, label="Meta ad flight")
    ticks = list(range(0, len(days), 10))
    axes.set_xticks(ticks)
    axes.set_xticklabels([dates[i][5:] for i in ticks], fontsize=9)
    axes.set_ylabel("sessions")
    axes.set_title("Daily sessions and cart additions — 85% of days have zero carts",
                   fontsize=13, pad=10)
    axes.legend(frameon=False, fontsize=9)
    axes.spines[["top", "right"]].set_visible(False)
    figure.tight_layout()
    path = REPORTS / "daily_trend.png"
    figure.savefig(path, dpi=150)
    plt.close(figure)
    print(f"\nchart written to {path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
