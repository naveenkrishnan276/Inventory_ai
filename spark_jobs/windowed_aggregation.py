"""
PySpark Structured Streaming — Windowed Aggregation Job

Reads retail sales events from a TCP socket on localhost:9999,
applies a 5-minute sliding window (1-minute slide) grouped by
store_id and product_id, and computes real-time sales aggregations.
"""

import os
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
# Spark session
# ---------------------------------------------------------------------------
spark = (
    SparkSession.builder
    .appName("RetailSalesWindowedAggregation")
    .master("local[*]")
    .getOrCreate()
)

spark.sparkContext.setLogLevel("WARN")

# ---------------------------------------------------------------------------
# Read from socket source
# ---------------------------------------------------------------------------
raw_stream = (
    spark.readStream
    .format("socket")
    .option("host", "localhost")
    .option("port", 9999)
    .load()
)

# ---------------------------------------------------------------------------
# Parse JSON → apply schema → extract timestamp
# ---------------------------------------------------------------------------
parsed_stream = (
    raw_stream
    .select(from_json(col("value"), SALES_SCHEMA).alias("data"))
    .select("data.*")
    .withColumn("event_time", to_timestamp(col("event_time")))
)

# ---------------------------------------------------------------------------
# Filter invalid records
# ---------------------------------------------------------------------------
valid_stream = parsed_stream.filter(
    (col("unit_price") > 0) & (col("quantity") > 0)
)

# ---------------------------------------------------------------------------
# Watermark (10 minutes) + sliding window (5 min window, 1 min slide)
# ---------------------------------------------------------------------------
windowed_agg = (
    valid_stream
    .withWatermark("event_time", "10 minutes")
    .groupBy(
        window(col("event_time"), "5 minutes", "1 minute"),
        col("store_id"),
        col("product_id"),
    )
    .agg(
        _sum("quantity").alias("total_units_sold"),
        _round(_sum(col("quantity") * col("unit_price")), 2).alias("total_revenue"),
        count("*").alias("transaction_count"),
    )
    .withColumn("avg_units_per_minute", _round(col("total_units_sold") / 5, 2))
)

# ---------------------------------------------------------------------------
# Select columns in a readable order
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
# Write to console in update mode
# ---------------------------------------------------------------------------
query = (
    output_stream.writeStream
    .outputMode("update")
    .format("console")
    .option("truncate", False)
    .trigger(processingTime="5 seconds")
    .start()
)

print("Windowed aggregation started — waiting for events on localhost:9999 …")
query.awaitTermination()
