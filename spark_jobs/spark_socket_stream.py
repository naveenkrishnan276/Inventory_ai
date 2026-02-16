"""
PySpark Structured Streaming job that reads retail sales events
from a TCP socket on localhost:9999, validates and cleans the data,
and writes the results to the console in append mode.
"""

import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Set HADOOP_HOME before importing PySpark (required on Windows)
# ---------------------------------------------------------------------------
HADOOP_HOME = str(Path(__file__).resolve().parent.parent / "hadoop")
os.environ["HADOOP_HOME"] = HADOOP_HOME
os.environ["hadoop.home.dir"] = HADOOP_HOME
# Ensure hadoop\bin is on PATH so winutils.exe is found
os.environ["PATH"] = os.path.join(HADOOP_HOME, "bin") + os.pathsep + os.environ.get("PATH", "")

from pyspark.sql import SparkSession
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType, IntegerType, BooleanType,
)
from pyspark.sql.functions import col, from_json, to_timestamp

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
    .appName("RetailSalesSocketStream")
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
# Watermark on event_time (tolerate up to 10 seconds of late data)
# ---------------------------------------------------------------------------
watermarked_stream = parsed_stream.withWatermark("event_time", "10 seconds")

# ---------------------------------------------------------------------------
# Filter out invalid records (negative price or quantity)
# ---------------------------------------------------------------------------
cleaned_stream = watermarked_stream.filter(
    (col("unit_price") > 0) & (col("quantity") > 0)
)

# ---------------------------------------------------------------------------
# Write to console in append mode
# ---------------------------------------------------------------------------
query = (
    cleaned_stream.writeStream
    .outputMode("append")
    .format("console")
    .option("truncate", False)
    .trigger(processingTime="2 seconds")
    .start()
)

print("Streaming started — waiting for events on localhost:9999 …")
query.awaitTermination()
