# PySpark Structured Streaming — Windowed Aggregation

Real-time sliding-window sales aggregations grouped by store and product.

## How It Works

```
sales_stream.py (TCP server :9999) ──► windowed_aggregation.py ──► console
```

1. Connects to the sales stream server on `localhost:9999`.
2. Parses JSON events and converts `event_time` to timestamp.
3. Filters out invalid records (negative price or quantity).
4. Applies a **10-minute watermark** on `event_time`.
5. Groups by **store_id**, **product_id**, and a **5-minute sliding window** (1-minute slide).
6. Computes aggregations and writes results to console in **update** mode every 5 seconds.

## Aggregations

| Metric | Formula |
|---|---|
| `total_units_sold` | `sum(quantity)` |
| `total_revenue` | `sum(quantity × unit_price)` |
| `avg_units_per_minute` | `total_units_sold / 5` |
| `transaction_count` | `count(*)` |

## Output Schema

| Column | Type | Description |
|---|---|---|
| `window_start` | Timestamp | Start of the 5-minute window |
| `window_end` | Timestamp | End of the 5-minute window |
| `store_id` | String | Store identifier |
| `product_id` | String | Product identifier |
| `total_units_sold` | Long | Total quantity sold in the window |
| `total_revenue` | Double | Total revenue (₹) in the window |
| `avg_units_per_minute` | Double | Average units sold per minute |
| `transaction_count` | Long | Number of transactions in the window |

## Usage

**Terminal 1 — Start the stream server:**

```bash
python data_stream/sales_stream.py
```

**Terminal 2 — Start the windowed aggregation job:**

```bash
python spark_jobs/windowed_aggregation.py
```

### Sample Console Output

```
-------------------------------------------
Batch: 5
-------------------------------------------
+-------------------+-------------------+---------+----------+----------------+-------------+--------------------+-----------------+
|window_start       |window_end         |store_id |product_id|total_units_sold|total_revenue|avg_units_per_minute|transaction_count|
+-------------------+-------------------+---------+----------+----------------+-------------+--------------------+-----------------+
|2026-02-16 18:05:00|2026-02-16 18:10:00|STORE_003|PROD_017  |6               |255.0        |1.2                 |2                |
|2026-02-16 18:05:00|2026-02-16 18:10:00|STORE_001|PROD_035  |4               |268.8        |0.8                 |1                |
+-------------------+-------------------+---------+----------+----------------+-------------+--------------------+-----------------+
```

## Configuration

| Setting | Value | Location |
|---|---|---|
| Socket host | `localhost` | `windowed_aggregation.py` |
| Socket port | `9999` | `windowed_aggregation.py` |
| Window duration | `5 minutes` | `windowed_aggregation.py` |
| Slide interval | `1 minute` | `windowed_aggregation.py` |
| Watermark delay | `10 minutes` | `windowed_aggregation.py` |
| Trigger interval | `5 seconds` | `windowed_aggregation.py` |

## Requirements

- Python 3.8+
- Apache Spark 3.x / PySpark (`pip install pyspark`)
- `data_stream/sales_stream.py` must be running first
