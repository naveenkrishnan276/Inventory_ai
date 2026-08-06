"""
PySpark Structured Streaming — Retail Sales Aggregation with Parquet Output

Reads retail sales events from a TCP socket on localhost:9999,
applies watermarking and sliding window aggregation, and writes
the aggregated results to Parquet format with checkpointing for
fault tolerance.

Features:
- 10-minute watermarking on event_time
- 5-minute sliding window with 1-minute slide interval
- Aggregations by store_id and product_id
- Parquet output partitioned by store_id and product_id
- Checkpoint directory for fault tolerance
- Continuous execution without termination
"""

import os
import shutil
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Set HADOOP_HOME before importing PySpark (required on Windows)
# ---------------------------------------------------------------------------
HADOOP_HOME = str(Path(__file__).resolve().parent.parent / "hadoop")
os.environ["HADOOP_HOME"] = HADOOP_HOME
os.environ["hadoop.home.dir"] = HADOOP_HOME
os.environ["PATH"] = os.path.join(HADOOP_HOME, "bin") + os.pathsep + os.environ.get("PATH", "")

from pyspark.sql import SparkSession
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType, IntegerType, BooleanType,
)
from pyspark.sql.functions import (
    col, from_json, to_timestamp, window,
    sum as _sum, count, round as _round,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
CHECKPOINT_DIR = "s3a://inventory-ai-data-nkr/checkpoints/retail_streaming"
OUTPUT_DIR = "s3a://inventory-ai-data-nkr/retail_aggregations"

# ---------------------------------------------------------------------------
# Clear stale checkpoints from previous runs.
# The socket source is in-memory only — it does NOT support recovery.
# Leftover checkpoints cause Spark to commit at offsets that no longer
# exist in the (empty) socket buffer, triggering:
#   java.lang.IndexOutOfBoundsException: at 0 deleting N
# ---------------------------------------------------------------------------
# Note: Since checkpoints are now on S3, you must manually delete the S3 folder
# before restarting the socket stream to avoid stale state issues.
print(f"IMPORTANT: Ensure you deleted stale checkpoints from S3 if restarting the stream!")

# ---------------------------------------------------------------------------
# Schema matching the events produced by sales_stream.py
# ---------------------------------------------------------------------------
SALES_SCHEMA = StructType([
    StructField("event_time", StringType(), True),
    StructField("store_id", StringType(), True),
    StructField("product_id", StringType(), True),
    StructField("category", StringType(), True),
    StructField("unit_price", DoubleType(), True),
    StructField("quantity", IntegerType(), True),
    StructField("payment_mode", StringType(), True),
    StructField("is_anomaly", BooleanType(), True),
])

# ---------------------------------------------------------------------------
# Spark session with optimized configurations
# ---------------------------------------------------------------------------
spark = (
    SparkSession.builder
    .appName("RetailSalesStreamingAggregation")
    .master("local[*]")
    .config("spark.sql.streaming.schemaInference", "false")
    .config("spark.sql.shuffle.partitions", "4")
    .config("spark.jars.packages", "org.apache.hadoop:hadoop-aws:3.3.4")
    .config("spark.hadoop.fs.s3a.aws.credentials.provider", "com.amazonaws.auth.InstanceProfileCredentialsProvider,com.amazonaws.auth.DefaultAWSCredentialsProviderChain")
    .getOrCreate()
)

spark.sparkContext.setLogLevel("WARN")

# ---------------------------------------------------------------------------
# Read from socket source on localhost:9999
# ---------------------------------------------------------------------------
raw_stream = (
    spark.readStream
    .format("socket")
    .option("host", "localhost")
    .option("port", 9999)
    .load()
)

# ---------------------------------------------------------------------------
# Parse JSON data using explicit schema and convert event_time to timestamp
# ---------------------------------------------------------------------------
parsed_stream = (
    raw_stream
    .select(from_json(col("value"), SALES_SCHEMA).alias("data"))
    .select("data.*")
    .withColumn("event_time", to_timestamp(col("event_time")))
)

# ---------------------------------------------------------------------------
# Filter out invalid records (negative price or quantity)
# ---------------------------------------------------------------------------
valid_stream = parsed_stream.filter(
    (col("unit_price") > 0) & (col("quantity") > 0)
)

# ---------------------------------------------------------------------------
# Apply watermarking of 10 minutes on event_time
# Watermarking allows the system to track late-arriving data and
# automatically drop events that are too old
# ---------------------------------------------------------------------------
watermarked_stream = valid_stream.withWatermark("event_time", "5 seconds")

# ---------------------------------------------------------------------------
# Perform sliding window aggregation (Accelerated for Demo):
# - Window duration: 30 seconds
# - Slide duration: 10 seconds
# - Group by: window, store_id, product_id
# ---------------------------------------------------------------------------
windowed_agg = (
    watermarked_stream
    .groupBy(
        window(col("event_time"), "30 seconds", "10 seconds"),
        col("store_id"),
        col("product_id"),
    )
    .agg(
        _sum("quantity").alias("total_units_sold"),
        _round(_sum(col("quantity") * col("unit_price")), 2).alias("total_revenue"),
        count("*").alias("transaction_count"),
    )
    .withColumn("avg_units_per_minute", _round(col("total_units_sold") * 2, 2))
)

# ---------------------------------------------------------------------------
# Select and structure output columns
# ---------------------------------------------------------------------------
output_stream = windowed_agg.select(
    col("window.start").alias("window_start"),
    col("window.end").alias("window_end"),
    "store_id",
    "product_id",
    "total_units_sold",
    "total_revenue",
    "avg_units_per_minute",
    "transaction_count",
)

# ---------------------------------------------------------------------------
# Write aggregated streaming output to disk in Parquet format
# - Output mode: append (new aggregation results are appended)
# - Format: parquet (columnar storage format, efficient for analytics)
# - Partitioned by: store_id and product_id (improves query performance)
# - Checkpoint location: permanent directory for fault tolerance
# - Processing trigger: 5 seconds (batch micro-batches every 5 seconds)
# ---------------------------------------------------------------------------
query = (
    output_stream.writeStream
    .outputMode("append")
    .format("parquet")
    .option("path", OUTPUT_DIR)
    .option("checkpointLocation", CHECKPOINT_DIR)
    .partitionBy("store_id", "product_id")
    .trigger(processingTime="5 seconds")
    .start()
)

# ---------------------------------------------------------------------------
# Run continuously without termination
# The job will keep running until manually stopped (Ctrl+C)
# ---------------------------------------------------------------------------
print(f"Streaming aggregation started...")
print(f"Checkpoint directory: {CHECKPOINT_DIR}")
print(f"Output directory: {OUTPUT_DIR}")
print(f"Waiting for events on localhost:9999...")
print(f"Press Ctrl+C to stop.")

query.awaitTermination()
