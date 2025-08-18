-- What to look for:
-- If the output only shows a single row for `items_per_return` = 1, it confirms
-- the generator is not creating realistic, multi-item returns.
WITH return_item_counts AS (
  SELECT
    return_id,
    COUNT(return_item_id) AS items_per_return
  FROM return_items
  GROUP BY
    1
)
SELECT
  items_per_return,
  COUNT(return_id) AS number_of_returns
FROM return_item_counts
GROUP BY
  1
ORDER BY
  1;
-- What to look for:
-- A very stable `decay_rate_pct` (e.g., always between 40-50%) for each cohort
-- month after month. Real data would show much more fluctuation.
WITH signup_cohorts AS (
  SELECT
    customer_id,
    STRFTIME('%Y-%m-01', signup_date) AS cohort_month
  FROM customers
  WHERE
    is_guest = FALSE
),
activity AS (
  SELECT
    customer_id,
    STRFTIME('%Y-%m-01', order_date) AS activity_month
  FROM orders
),
cohort_monthly_activity AS (
  SELECT
    c.cohort_month,
    a.activity_month,
    COUNT(DISTINCT c.customer_id) AS active_users
  FROM signup_cohorts c
  JOIN activity a
    ON c.customer_id = a.customer_id
  GROUP BY
    1,
    2
),
retention_decay AS (
  SELECT
    cohort_month,
    activity_month,
    active_users,
    LAG(active_users, 1, active_users) OVER (PARTITION BY cohort_month ORDER BY activity_month) AS prev_month_users
  FROM cohort_monthly_activity
)
SELECT
  cohort_month,
  activity_month,
  (1.0 - (active_users * 1.0 / prev_month_users)) * 100 AS decay_rate_pct
FROM retention_decay
WHERE
  cohort_month <= STRFTIME('%Y-%m-01', DATE('now', '-4 months')) -- Focus on mature cohorts
ORDER BY
  1,
  2;
-- What to look for:
-- If this query returns no rows, it confirms that no customer's loyalty tier
-- ever changes, highlighting the simplified segmentation logic.
SELECT
  customer_id,
  COUNT(DISTINCT customer_tier) AS distinct_tiers_on_orders
FROM orders
WHERE
  customer_id IS NOT NULL
GROUP BY
  1
HAVING
  distinct_tiers_on_orders > 1;
-- What to look for:
-- The percentages for Low, Medium, and High will be almost identical for every
-- `signup_channel`, confirming the lack of differentiation.
WITH channel_clv_counts AS (
  SELECT
    signup_channel,
    clv_bucket,
    COUNT(customer_id) AS num_customers
  FROM customers
  WHERE
    signup_channel IS NOT NULL AND clv_bucket IS NOT NULL
  GROUP BY
    1,
    2
),
channel_totals AS (
  SELECT
    signup_channel,
    SUM(num_customers) AS total_customers
  FROM channel_clv_counts
  GROUP BY
    1
)
SELECT
  c.signup_channel,
  c.clv_bucket,
  c.num_customers,
  t.total_customers,
  ROUND(c.num_customers * 100.0 / t.total_customers, 2) AS percentage_of_channel
FROM channel_clv_counts c
JOIN channel_totals t
  ON c.signup_channel = t.signup_channel
ORDER BY
  1,
  5 DESC;
