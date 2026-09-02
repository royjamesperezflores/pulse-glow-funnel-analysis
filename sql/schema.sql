CREATE TABLE IF NOT EXISTS session_metrics_daily (
  date TEXT NOT NULL,
  dimension TEXT NOT NULL,
  dimension_value TEXT NOT NULL,
  sessions INTEGER NOT NULL,
  cart_add_sessions INTEGER NOT NULL,
  checkout_sessions INTEGER NOT NULL,
  completed_sessions INTEGER NOT NULL,
  PRIMARY KEY (date, dimension, dimension_value)
);
