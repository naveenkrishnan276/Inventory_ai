# Real-Time Retail Sales Stream Generator

Runs a TCP server on `localhost:9999` that continuously generates retail sales events and streams them as newline-delimited JSON to any connected client (e.g. PySpark Structured Streaming).

## Files

| File | Description |
|---|---|
| `sales_stream.py` | TCP server + event generator — listens on `localhost:9999` and pushes events to connected clients |

## Event Schema

```json
{
  "event_time": "2026-02-16T12:21:59.374733+00:00",
  "store_id": "STORE_003",
  "product_id": "PROD_017",
  "category": "Snacks",
  "unit_price": 42.5,
  "quantity": 3,
  "payment_mode": "UPI",
  "is_anomaly": false
}
```

| Field | Description |
|---|---|
| `event_time` | UTC timestamp in ISO 8601 format |
| `store_id` | One of `STORE_001` – `STORE_005` |
| `product_id` | One of `PROD_001` – `PROD_050` |
| `category` | Rice, Snacks, Beverages, Dairy, or Personal Care |
| `unit_price` | Realistic price (INR) based on category |
| `quantity` | 1–5 (normal) or 10–50 (anomaly) |
| `payment_mode` | UPI, Card, or Cash |
| `is_anomaly` | `true` when a price/quantity spike is injected |

## Product → Category Mapping

| Product Range | Category |
|---|---|
| PROD_001 – PROD_010 | Rice |
| PROD_011 – PROD_020 | Snacks |
| PROD_021 – PROD_030 | Beverages |
| PROD_031 – PROD_040 | Dairy |
| PROD_041 – PROD_050 | Personal Care |

## Anomalies

~5 % of events are injected as anomalies:

- **Price spike** — 2× to 5× the normal category maximum
- **High quantity** — 10 to 50 units instead of the usual 1–5

## Usage

**Terminal 1 — Start the stream server:**

```bash
python data_stream/sales_stream.py
```

**Terminal 2 — Start the PySpark consumer:**

```bash
python spark_job_socket/spark_socket_stream.py
```

See [`spark_job_socket/README.md`](../spark_job_socket/README.md) for full details on the Structured Streaming consumer.

Events are generated every 1–2 seconds and broadcast to all connected clients. Multiple clients can connect simultaneously.

## Architecture

```
sales_stream.py (TCP server on :9999)
       │
       ├──► PySpark Structured Streaming
       ├──► Any other TCP client
       └──► (console output)
```

## Requirements

- Python 3.8+
- No external dependencies (uses only the standard library)
- For the PySpark consumer: Apache Spark 3.x / PySpark (`pip install pyspark`)
