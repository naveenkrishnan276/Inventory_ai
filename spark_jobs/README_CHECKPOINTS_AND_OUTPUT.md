# Checkpoints and Output in PySpark Structured Streaming

This document explains the two critical components of the retail streaming aggregation job: **Checkpoints** and **Output**.

---

## Checkpoints

### What Are Checkpoints?

Checkpoints are a **fault-tolerance mechanism** in PySpark Structured Streaming. They store the state and progress of the streaming query so it can recover from failures without losing data or processing duplicates.

### Location

```
checkpoints/retail_streaming/
```

### Purpose

- **Recovery**: If the job crashes, it can restart from the last checkpoint and resume processing
- **Exactly-once semantics**: Ensures no data is lost or duplicated during recovery
- **State tracking**: Maintains internal state for windowed aggregations and late data handling
- **Idempotent writing**: Prevents writing the same results twice if the job restarts

### Directory Structure

```
checkpoints/retail_streaming/
├── metadata                    # Metadata about the checkpoint
├── commits/                    # Commit logs (numbered 0, 1, 2, ...)
│   ├── 0
│   ├── 1
│   ├── 2
│   └── ...
└── offsets/                    # Offset tracking (if applicable)
```

### What Each File Does

| Component | Purpose |
|-----------|---------|
| `metadata` | Tracks the checkpoint version and schema information |
| `commits/0, /1, /2, ...` | Records each micro-batch execution (numbered sequentially) |
| `.crc` files | Checksum files for data integrity verification |

### Example Recovery Scenario

```
Time 0:00  → Job starts, processes batches 0-10, checkpoints at batch 10
Time 0:45  → Job crashes after processing batch 25
Time 0:50  → Job restarts, reads checkpoint, resumes from batch 25
           → Only new data after batch 25 is reprocessed
           → No duplicate writes to output
```

### Checkpoint Size

- **Typical size**: Grows slowly over time (a few MB after hours of streaming)
- **Why it grows**: New commit logs added with each micro-batch
- **Cleanup**: Can be archived/deleted after the job runs for days without issues
- **Important**: Keep the checkpoint until you're confident the job is stable

---

## Output

### What Is Output?

Output is the **actual aggregated data** written to Parquet files. This is the analytics-ready result of your streaming job.

### Location

```
output/retail_aggregations/
```

### Format

- **File format**: Parquet (columnar format, efficient for analytics)
- **Compression**: Snappy (fast, good compression ratio)
- **Partitioned by**: `store_id` and `product_id` (improves query performance)

### Directory Structure

```
output/retail_aggregations/
├── store_id=STORE_001/
│   ├── product_id=PROD_001/
│   │   ├── part-00000-abc123.snappy.parquet
│   │   ├── part-00001-xyz789.snappy.parquet
│   │   └── ...
│   ├── product_id=PROD_002/
│   │   └── part-00000-def456.snappy.parquet
│   └── ...
├── store_id=STORE_002/
│   └── ...
└── _spark_metadata/            # Output metadata (for Spark to read the data)
```

### Data in Each Parquet File

Each row contains:

| Column | Type | Example |
|--------|------|---------|
| `window_start` | Timestamp | 2026-02-22 10:00:00 |
| `window_end` | Timestamp | 2026-02-22 10:05:00 |
| `store_id` | String | STORE_001 |
| `product_id` | String | PROD_015 |
| `total_units_sold` | Long | 42 |
| `total_revenue` | Double | 1250.50 |
| `avg_units_per_minute` | Double | 8.4 |
| `transaction_count` | Long | 12 |

### Example Output

```
Window: 10:00 - 10:05
┌──────────────┬──────────┬─────────────────┬──────────────┬──────────────────┐
│ store_id     │ product  │ units_sold      │ revenue      │ transactions     │
├──────────────┼──────────┼─────────────────┼──────────────┼──────────────────┤
│ STORE_001    │ PROD_015 │ 42              │ 1250.50      │ 12               │
│ STORE_001    │ PROD_023 │ 18              │ 450.00       │ 5                │
│ STORE_002    │ PROD_001 │ 75              │ 3000.00      │ 20               │
└──────────────┴──────────┴─────────────────┴──────────────┴──────────────────┘
```

### When Output Appears

- **First window closes after**: 5 minutes of streaming (the window duration)
- **New files added**: Every 5 minutes (sliding window with 1-minute slides)
- **Files created**: With each trigger interval (every 5 seconds in this job)

### Example Timeline

```
Time    Event
────────────────────────────────────────────────────────
0:00    Job starts, window [0:00-0:05] opens
0:05    First window [0:00-0:05] closes → PARQUET FILE 1 written
0:06    Second window [0:01-0:06] closes → PARQUET FILE 2 written
0:07    Third window [0:02-0:07] closes → PARQUET FILE 3 written
0:08    Fourth window [0:03-0:08] closes → PARQUET FILE 4 written
...     (overlapping windows, new files every minute after the first)
```

### Output Size

- **Per window**: Depends on data volume (typically 1KB - 100KB per file)
- **Growth rate**: ~1-10 MB per hour (varies by event volume)
- **Partition benefit**: Makes querying specific stores/products fast

---

## How Checkpoints and Output Work Together

### The Streaming Pipeline

```
┌─────────────┐
│ Socket      │  ← Reads from localhost:9999
├─────────────┤
│ Parse JSON  │  ← Extracts fields
├─────────────┤
│ Watermark   │  ← 10-minute tolerance
├─────────────┤
│ Window      │  ← 5-minute windows, 1-minute slides
├─────────────┤
│ Aggregate   │  ← Sum, count, avg calculations
├─────────────┤
│ CHECKPOINT  │  ← State saved every micro-batch ✓
├─────────────┤
│ Write Disk  │  ← Parquet files written to output/ ✓
└─────────────┘
```

### Failure Scenario

```
Normal Run:
  Batch 1 → 100 → Checkpoint 100 → Write output 100
  Batch 101 → 150 → Checkpoint 150 → Write output 150
  
After Crash/Restart:
  System reads Checkpoint 150
  Resumes from Batch 151 (NEW DATA ONLY)
  No duplicate writes to output
```

---

## Best Practices

### Checkpoints

✓ **DO:**
- Keep checkpoints for at least the job's expected lifetime
- Store on reliable, fast storage (SSD preferred)
- Monitor checkpoint directory size periodically
- Back up checkpoints for critical jobs

✗ **DON'T:**
- Delete checkpoints while the job is running
- Share checkpoints between different job versions
- Edit checkpoint files manually
- Expect checkpoints to be human-readable (they're binary)

### Output

✓ **DO:**
- Query output with Spark SQL or PySpark DataFrame API
- Use partitions in queries for faster performance
- Archive old data periodically (e.g., older than 30 days)
- Monitor output directory size

✗ **DON'T:**
- Edit Parquet files manually
- Expect output to be immediately available (window timing matters)
- Use output for real-time querying (it's batched aggregations)
- Rely on file modification times for ordering

---

## Querying Output with Spark

### Read All Aggregated Data

```python
from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("ReadAggregations").getOrCreate()

df = spark.read.parquet("output/retail_aggregations/")
df.show()
```

### Query Specific Store

```python
df_store_001 = spark.read.parquet("output/retail_aggregations/store_id=STORE_001/")
df_store_001.show()
```

### Query Specific Product in Specific Store

```python
df_product = spark.read.parquet(
    "output/retail_aggregations/store_id=STORE_001/product_id=PROD_015/"
)
df_product.show()
```

### SQL Query

```python
spark.sql("""
    SELECT store_id, product_id, window_start, total_revenue
    FROM parquet.`output/retail_aggregations/`
    WHERE store_id = 'STORE_001'
    ORDER BY window_start DESC
    LIMIT 10
""").show()
```

---

## Troubleshooting

### Problem: Job Crashes and Doesn't Resume

**Cause**: Checkpoint directory was deleted or moved
**Solution**: Restart from beginning, accept loss of state

### Problem: Output Directory Growing Too Large

**Cause**: Streaming for days without archival
**Solution**: Archive old partitions to backup storage

### Problem: Duplicate Data in Output After Restart

**Cause**: Checkpoint was deleted but job config remained
**Solution**: Use checkpoint for job restarts (never delete during production)

### Problem: No Output Files Appearing

**Cause**: 
- Job just started (need to wait for first window to close)
- Job crashed (check logs, restart with checkpoint)
- Socket connection failed (verify localhost:9999 is available)

**Solution**: Wait 5+ minutes, check job logs, verify data producer is running

---

## Summary Table

| Aspect | Checkpoint | Output |
|--------|-----------|--------|
| **Purpose** | Fault tolerance & recovery | Final aggregated results |
| **Format** | Binary checkpoint files | Parquet files |
| **Location** | `checkpoints/retail_streaming/` | `output/retail_aggregations/` |
| **Human Readable** | No | Yes (with Spark) |
| **Growth** | Slow (MB over hours) | Moderate (MB/hour) |
| **When Used** | After every micro-batch | When window closes |
| **Query-able** | No | Yes |
| **Delete After Crash** | No | No |
| **Essential** | Yes (for recovery) | Yes (for analytics) |
