"""
PySpark Inventory Decision Engine

Uses a trained Random Forest regression model to predict demand and generate
intelligent inventory management decisions.

Workflow:
    1. Load aggregated demand features from Parquet (output/retail_aggregations)
    2. Load current inventory data from CSV (data/current_inventory.csv)
    3. Load trained Random Forest model (models/demand_rf_model)
    4. Predict demand per store and product (5-minute window)
    5. Convert to daily demand (multiply by 288: 24*60/5)
    6. Calculate stock-out risk based on current stock and lead time
    7. Generate reorder recommendations
    8. Output actionable decision table

Risk Logic:
    HIGH   → current_stock < predicted_daily_demand * lead_time_days
    MEDIUM → current_stock < predicted_daily_demand * (lead_time_days + 1)
    LOW    → otherwise

Reorder Quantity:
    max(predicted_daily_demand * (lead_time_days + 2) - current_stock, 0)

Action:
    REORDER   → HIGH risk
    MONITOR   → MEDIUM risk
    NO_ACTION → LOW risk
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
from pyspark.ml import PipelineModel
from pyspark.sql.functions import (
    col, lit, when, max as sql_max, round as sql_round
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
RETAIL_AGGREGATIONS_PATH = str(Path(__file__).resolve().parent.parent / "output" / "retail_aggregations")
INVENTORY_CSV_PATH = str(Path(__file__).resolve().parent.parent / "data" / "current_inventory.csv")
MODEL_PATH = str(Path(__file__).resolve().parent.parent / "models" / "demand_rf_model")

# Model expects these feature columns
FEATURE_COLUMNS = [
    "total_units_sold",
    "total_revenue",
    "avg_units_per_minute",
    "transaction_count",
]

# 5-minute windows per day: 24 hours * 60 minutes / 5 minutes = 288
WINDOWS_PER_DAY = 288

# ---------------------------------------------------------------------------
# Initialize Spark Session
# ---------------------------------------------------------------------------
print("=" * 80)
print("Inventory Decision Engine - Initialization")
print("=" * 80)

spark = (
    SparkSession.builder
    .appName("InventoryDecisionEngine")
    .master("local[*]")
    .config("spark.sql.shuffle.partitions", "4")
    .getOrCreate()
)

spark.sparkContext.setLogLevel("WARN")
print("✓ Spark session initialized")

# ---------------------------------------------------------------------------
# 1. Load aggregated demand features from Parquet
# ---------------------------------------------------------------------------
print("\n" + "=" * 80)
print("Step 1: Loading Demand Features")
print("=" * 80)

try:
    # Read from partitioned parquet as batch data (ignore streaming metadata)
    # Set basePath to properly discover partition columns
    demand_df = (spark.read
                 .option("basePath", RETAIL_AGGREGATIONS_PATH)
                 .option("mergeSchema", "true")
                 .parquet(f"{RETAIL_AGGREGATIONS_PATH}/store_id=*/product_id=*/"))
    
    print(f"✓ Loaded demand features from: {RETAIL_AGGREGATIONS_PATH}")
    print(f"✓ Total records: {demand_df.count()}")
    print(f"✓ Columns: {demand_df.columns}")
    
    # Aggregate to get average demand metrics per store/product
    # (Since we may have multiple time windows, we'll take the most recent or average)
    demand_agg = demand_df.groupBy("store_id", "product_id").agg(
        sql_max("total_units_sold").alias("total_units_sold"),
        sql_max("total_revenue").alias("total_revenue"),
        sql_max("avg_units_per_minute").alias("avg_units_per_minute"),
        sql_max("transaction_count").alias("transaction_count"),
    )
    
    print(f"✓ Aggregated to unique store/product combinations: {demand_agg.count()}")
    
except Exception as e:
    print(f"✗ Error loading demand features: {e}")
    print("\nTroubleshooting:")
    print("  1. Ensure streaming aggregation job has run")
    print("  2. Check that output/retail_aggregations contains data")
    print(f"  3. Path: {RETAIL_AGGREGATIONS_PATH}")
    spark.stop()
    exit(1)

# ---------------------------------------------------------------------------
# 2. Load current inventory data from CSV
# ---------------------------------------------------------------------------
print("\n" + "=" * 80)
print("Step 2: Loading Current Inventory")
print("=" * 80)

try:
    inventory_df = spark.read.csv(
        INVENTORY_CSV_PATH,
        header=True,
        inferSchema=True
    )
    print(f"✓ Loaded inventory from: {INVENTORY_CSV_PATH}")
    print(f"✓ Total inventory records: {inventory_df.count()}")
    print(f"✓ Columns: {inventory_df.columns}")
    
    # Show sample inventory
    print("\nSample Inventory Data:")
    inventory_df.show(5, truncate=False)
    
except Exception as e:
    print(f"✗ Error loading inventory: {e}")
    print(f"\nPlease ensure {INVENTORY_CSV_PATH} exists with required columns:")
    print("  - store_id, product_id, current_stock, lead_time_days")
    spark.stop()
    exit(1)

# ---------------------------------------------------------------------------
# 3. Load trained Random Forest model
# ---------------------------------------------------------------------------
print("\n" + "=" * 80)
print("Step 3: Loading Trained Model")
print("=" * 80)

try:
    model = PipelineModel.load(MODEL_PATH)
    print(f"✓ Model loaded from: {MODEL_PATH}")
    print(f"✓ Pipeline stages: {len(model.stages)}")
    for i, stage in enumerate(model.stages, 1):
        print(f"  {i}. {stage.__class__.__name__}")
    
except Exception as e:
    print(f"✗ Error loading model: {e}")
    print(f"\nPlease ensure the model exists at: {MODEL_PATH}")
    print("Run demand_prediction_rf.py to train the model first.")
    spark.stop()
    exit(1)

# ---------------------------------------------------------------------------
# 4. Join inventory with demand features
# ---------------------------------------------------------------------------
print("\n" + "=" * 80)
print("Step 4: Joining Inventory with Demand Features")
print("=" * 80)

# Join on store_id and product_id
joined_df = inventory_df.join(
    demand_agg,
    on=["store_id", "product_id"],
    how="inner"
)

print(f"✓ Joined records: {joined_df.count()}")
print(f"✓ Columns after join: {joined_df.columns}")

# Show sample joined data
print("\nSample Joined Data:")
joined_df.select(
    "store_id", "product_id", "current_stock", "lead_time_days",
    "total_units_sold", "avg_units_per_minute"
).show(5, truncate=False)

# ---------------------------------------------------------------------------
# 5. Predict demand using the trained model
# ---------------------------------------------------------------------------
print("\n" + "=" * 80)
print("Step 5: Predicting Demand")
print("=" * 80)

# Ensure all feature columns are present
for col_name in FEATURE_COLUMNS:
    if col_name not in joined_df.columns:
        print(f"✗ Missing feature column: {col_name}")
        spark.stop()
        exit(1)

# Make predictions
predictions_df = model.transform(joined_df)
print(f"✓ Predictions generated")
print(f"✓ Prediction column added: 'prediction'")

# Show sample predictions
print("\nSample Predictions (5-minute window demand):")
predictions_df.select(
    "store_id", "product_id", "total_units_sold",
    "avg_units_per_minute", "prediction"
).show(5, truncate=False)

# ---------------------------------------------------------------------------
# 6. Convert predicted demand to daily demand
# ---------------------------------------------------------------------------
print("\n" + "=" * 80)
print("Step 6: Converting to Daily Demand")
print("=" * 80)

# Predicted demand is for 5-minute window, multiply by 288 for daily
predictions_with_daily = predictions_df.withColumn(
    "predicted_daily_demand",
    sql_round(col("prediction") * lit(WINDOWS_PER_DAY), 2)
)

print(f"✓ Daily demand calculated (prediction × {WINDOWS_PER_DAY})")
print("\nSample Daily Demand:")
predictions_with_daily.select(
    "store_id", "product_id", "prediction", "predicted_daily_demand"
).show(5, truncate=False)

# ---------------------------------------------------------------------------
# 7. Calculate stock-out risk
# ---------------------------------------------------------------------------
print("\n" + "=" * 80)
print("Step 7: Calculating Stock-Out Risk")
print("=" * 80)

risk_df = predictions_with_daily.withColumn(
    "stock_out_risk",
    when(
        col("current_stock") < (col("predicted_daily_demand") * col("lead_time_days")),
        lit("HIGH")
    ).when(
        col("current_stock") < (col("predicted_daily_demand") * (col("lead_time_days") + 1)),
        lit("MEDIUM")
    ).otherwise(
        lit("LOW")
    )
)

print("✓ Stock-out risk calculated")
print("\nRisk Logic:")
print("  HIGH   → current_stock < predicted_daily_demand × lead_time_days")
print("  MEDIUM → current_stock < predicted_daily_demand × (lead_time_days + 1)")
print("  LOW    → otherwise")

# Show risk distribution
print("\nRisk Distribution:")
risk_df.groupBy("stock_out_risk").count().orderBy(col("count").desc()).show()

# ---------------------------------------------------------------------------
# 8. Calculate recommended reorder quantity
# ---------------------------------------------------------------------------
print("\n" + "=" * 80)
print("Step 8: Calculating Recommended Reorder Quantity")
print("=" * 80)

reorder_df = risk_df.withColumn(
    "recommended_reorder_quantity",
    when(
        (col("predicted_daily_demand") * (col("lead_time_days") + 2) - col("current_stock")) > 0,
        sql_round(col("predicted_daily_demand") * (col("lead_time_days") + 2) - col("current_stock"), 0)
    ).otherwise(
        lit(0)
    )
)

print("✓ Reorder quantity calculated")
print("  Formula: max(predicted_daily_demand × (lead_time_days + 2) - current_stock, 0)")

# ---------------------------------------------------------------------------
# 9. Determine action
# ---------------------------------------------------------------------------
print("\n" + "=" * 80)
print("Step 9: Determining Action")
print("=" * 80)

decision_df = reorder_df.withColumn(
    "action",
    when(col("stock_out_risk") == "HIGH", lit("REORDER"))
    .when(col("stock_out_risk") == "MEDIUM", lit("MONITOR"))
    .otherwise(lit("NO_ACTION"))
)

print("✓ Actions assigned")
print("\nAction Logic:")
print("  REORDER   → HIGH risk")
print("  MONITOR   → MEDIUM risk")
print("  NO_ACTION → LOW risk")

# Show action distribution
print("\nAction Distribution:")
decision_df.groupBy("action").count().orderBy(col("count").desc()).show()

# ---------------------------------------------------------------------------
# 10. Create final decision table
# ---------------------------------------------------------------------------
print("\n" + "=" * 80)
print("Step 10: Final Decision Table")
print("=" * 80)

final_decision_df = decision_df.select(
    "store_id",
    "product_id",
    "current_stock",
    "predicted_daily_demand",
    "stock_out_risk",
    "recommended_reorder_quantity",
    "action"
).orderBy(
    col("action").desc(),  # REORDER first
    col("stock_out_risk").desc(),
    "store_id",
    "product_id"
)

print("✓ Final decision table created")
print(f"✓ Total decisions: {final_decision_df.count()}")

# ---------------------------------------------------------------------------
# 11. Display results
# ---------------------------------------------------------------------------
print("\n" + "=" * 80)
print("INVENTORY DECISION TABLE")
print("=" * 80)

# Show all decisions
final_decision_df.show(100, truncate=False)

# Show summary statistics
print("\n" + "=" * 80)
print("Summary Statistics")
print("=" * 80)

# Summary by action
print("\n--- By Action ---")
final_decision_df.groupBy("action").count() \
    .orderBy(col("count").desc()) \
    .show(truncate=False)

# Summary by risk
print("\n--- By Stock-Out Risk ---")
final_decision_df.groupBy("stock_out_risk").count() \
    .orderBy(col("count").desc()) \
    .show(truncate=False)

# Summary by store
print("\n--- By Store ---")
final_decision_df.groupBy("store_id").count() \
    .orderBy("store_id") \
    .show(truncate=False)

# High priority items (REORDER action)
print("\n" + "=" * 80)
print("HIGH PRIORITY - REORDER NOW")
print("=" * 80)
reorder_items = final_decision_df.filter(col("action") == "REORDER")
print(f"Total items requiring immediate reorder: {reorder_items.count()}")
if reorder_items.count() > 0:
    reorder_items.show(50, truncate=False)

# Medium priority items (MONITOR action)
print("\n" + "=" * 80)
print("MEDIUM PRIORITY - MONITOR CLOSELY")
print("=" * 80)
monitor_items = final_decision_df.filter(col("action") == "MONITOR")
print(f"Total items requiring monitoring: {monitor_items.count()}")
if monitor_items.count() > 0:
    monitor_items.show(50, truncate=False)

# Low priority items (NO_ACTION)
print("\n" + "=" * 80)
print("LOW PRIORITY - NO ACTION REQUIRED")
print("=" * 80)
no_action_items = final_decision_df.filter(col("action") == "NO_ACTION")
print(f"Total items with sufficient stock: {no_action_items.count()}")
if no_action_items.count() > 0:
    no_action_items.show(50, truncate=False)

# ---------------------------------------------------------------------------
# 12. Business insights
# ---------------------------------------------------------------------------
print("\n" + "=" * 80)
print("Business Insights")
print("=" * 80)

# Total reorder quantity needed
total_reorder = final_decision_df.agg({"recommended_reorder_quantity": "sum"}).collect()[0][0]
print(f"Total units to reorder across all items: {total_reorder:.0f}")

# Average predicted daily demand
avg_demand = final_decision_df.agg({"predicted_daily_demand": "avg"}).collect()[0][0]
print(f"Average predicted daily demand per product: {avg_demand:.2f}")

# Store with highest reorder needs
print("\nTop 5 stores by total reorder quantity:")
final_decision_df.groupBy("store_id") \
    .agg({"recommended_reorder_quantity": "sum"}) \
    .withColumnRenamed("sum(recommended_reorder_quantity)", "total_reorder_needed") \
    .orderBy(col("total_reorder_needed").desc()) \
    .show(5, truncate=False)

# Products with highest demand
print("\nTop 10 products by predicted daily demand:")
final_decision_df.groupBy("product_id") \
    .agg({"predicted_daily_demand": "sum"}) \
    .withColumnRenamed("sum(predicted_daily_demand)", "total_daily_demand") \
    .orderBy(col("total_daily_demand").desc()) \
    .show(10, truncate=False)

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------
print("\n" + "=" * 80)
print("Execution Complete")
print("=" * 80)
print("✓ Decision engine completed successfully")
print("✓ Use the decision table above to take inventory actions")

spark.stop()
print("✓ Spark session closed")
print("=" * 80)
