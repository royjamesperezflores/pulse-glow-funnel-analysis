-- Queries behind the findings. Run against data/funnel.db.
-- Metrics are stored long (one row per date x dimension x value), so every
-- question is the same shape: filter to a dimension, SUM across the window.

-- 1. The overall funnel, and the share surviving each stage.
SELECT SUM(sessions)                                                  AS sessions,
       SUM(cart_add_sessions)                                         AS cart_adds,
       SUM(checkout_sessions)                                         AS checkouts,
       SUM(completed_sessions)                                        AS orders,
       ROUND(100.0 * SUM(cart_add_sessions)  / SUM(sessions), 2)      AS cart_add_pct,
       ROUND(100.0 * SUM(checkout_sessions)  / NULLIF(SUM(cart_add_sessions), 0), 2)
                                                                      AS checkout_of_cart_pct,
       ROUND(100.0 * SUM(completed_sessions) / SUM(sessions), 2)      AS conversion_pct
FROM session_metrics_daily
WHERE dimension = 'day';

-- 2. Finding 1: does the page a visitor lands on change how far they get?
SELECT dimension_value                                                AS landing_page_type,
       SUM(sessions)                                                  AS sessions,
       SUM(cart_add_sessions)                                         AS cart_adds,
       ROUND(100.0 * SUM(cart_add_sessions) / SUM(sessions), 2)       AS cart_add_pct
FROM session_metrics_daily
WHERE dimension = 'landing_page_type'
GROUP BY dimension_value
ORDER BY sessions DESC;

-- 3. The confound: how much of that gap is bot traffic, not shopper intent?
--    Values are stored as 'landing page type | Human'.
SELECT dimension_value                                                AS landing_type_and_bot_flag,
       SUM(sessions)                                                  AS sessions,
       SUM(cart_add_sessions)                                         AS cart_adds,
       ROUND(100.0 * SUM(cart_add_sessions) / SUM(sessions), 2)       AS cart_add_pct
FROM session_metrics_daily
WHERE dimension = 'landing_page_type+human_or_bot_session'
GROUP BY dimension_value
ORDER BY sessions DESC;

-- 4. Where the money leaks: sessions that reached checkout but never completed.
SELECT dimension_value,
       SUM(checkout_sessions)                                         AS reached_checkout,
       SUM(completed_sessions)                                        AS completed,
       SUM(checkout_sessions) - SUM(completed_sessions)               AS abandoned,
       ROUND(100.0 * (SUM(checkout_sessions) - SUM(completed_sessions))
             / NULLIF(SUM(checkout_sessions), 0), 2)                  AS abandon_pct
FROM session_metrics_daily
WHERE dimension = 'session_device_type'
GROUP BY dimension_value
ORDER BY abandoned DESC;

-- 5. Daily trend, to separate a real pattern from one loud day.
SELECT date,
       sessions,
       cart_add_sessions,
       completed_sessions
FROM session_metrics_daily
WHERE dimension = 'day'
ORDER BY date;
