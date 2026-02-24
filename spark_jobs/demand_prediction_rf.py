"""
PySpark MLlib Random Forest Regression — Demand Prediction Model

Trains a Random Forest regression model to predict product demand using
aggregated streaming data from the retail_aggregations Parquet dataset.
Uses MLlib Pipelines for robust model training and evaluation.

Features:
    - total_units_sold
    - total_revenue
    - avg_units_per_minute
    - transaction_count
    - store_id (indexed)
    - product_id (indexed)

Label:
    - total_units_sold (next-window demand proxy)

Output:
    - Trained model saved to: models/demand_rf_model
    - Feature importance printed to console
    - Model evaluation metrics (RMSE, R2)
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
from pyspark.ml import Pipeline
from pyspark.ml.feature import VectorAssembler
from pyspark.ml.regression import RandomForestRegressor
from pyspark.ml.evaluation import RegressionEvaluator

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
INPUT_PATH = str(Path(__file__).resolve().parent.parent / "output" / "retail_aggregations")
MODEL_OUTPUT_PATH = str(Path(__file__).resolve().parent.parent / "models" / "demand_rf_model")

FEATURE_COLUMNS = [
    "total_units_sold",
    "total_revenue",
    "avg_units_per_minute",
    "transaction_count",
]
CATEGORICAL_COLUMNS = []  # No categorical columns available in partitioned output
LABEL_COLUMN = "total_units_sold"

# ---------------------------------------------------------------------------
# Spark session with optimized configurations
# ---------------------------------------------------------------------------
spark = (
    SparkSession.builder
    .appName("DemandPredictionRandomForest")
    .master("local[*]")
    .config("spark.sql.shuffle.partitions", "4")
    .getOrCreate()
)

spark.sparkContext.setLogLevel("WARN")

# ---------------------------------------------------------------------------
# Read aggregated streaming data from Parquet
# Skip _spark_metadata directory by using partition pattern
# ---------------------------------------------------------------------------
print("=" * 80)
print("Reading aggregated data from Parquet...")
print("=" * 80)

try:
    # Use glob pattern to read only partition directories, avoid _spark_metadata
    parquet_pattern = f"{INPUT_PATH}/store_id=*/product_id=*"
    df = spark.read.parquet(parquet_pattern)
    print(f"Loaded data from: {parquet_pattern}")
    print(f"Total records: {df.count()}")
    print(f"Schema:")
    df.printSchema()
except Exception as e:
    print(f"Error reading Parquet data: {e}")
    print("\n  Troubleshooting:")
    print("  1. Ensure streaming job has been running for at least 5 minutes")
    print("  2. Check that output/retail_aggregations/store_id=*/product_id=*/ directories exist")
    print("  3. Verify data producer (sales_stream.py) is running on localhost:9999")
    print(f"\n  Looking for files in: {parquet_pattern}")
    spark.stop()
    exit(1)

# ---------------------------------------------------------------------------
# Data exploration
# ---------------------------------------------------------------------------
print("\n" + "=" * 80)
print("Data Exploration")
print("=" * 80)
print(f"Total rows: {df.count()}")
print(f"Null value counts:")

# Check for null values in each column
for c in df.columns:
    null_count = df.filter(df[c].isNull()).count()
    print(f"  {c}: {null_count}")

# ---------------------------------------------------------------------------
# Drop rows with null values
# ---------------------------------------------------------------------------
print("\n" + "=" * 80)
print("Data Cleaning: Removing rows with null values...")
print("=" * 80)

df_clean = df.dropna()
rows_removed = df.count() - df_clean.count()
print(f"Rows removed: {rows_removed}")
print(f"Rows remaining: {df_clean.count()}")

# ---------------------------------------------------------------------------
# Build ML Pipeline
# ---------------------------------------------------------------------------
print("\n" + "=" * 80)
print("Building ML Pipeline...")
print("=" * 80)

# Note: store_id and product_id are partition columns (not in the data)
# Only numeric features are available

# Stage 1: VectorAssembler to combine all features
vector_assembler = VectorAssembler(
    inputCols=FEATURE_COLUMNS,
    outputCol="features",
    handleInvalid="skip"
)

# Stage 2: RandomForestRegressor
rf = RandomForestRegressor(
    featuresCol="features",
    labelCol=LABEL_COLUMN,
    numTrees=100,
    maxDepth=10,
    minInstancesPerNode=1,
    seed=42,
    featureSubsetStrategy="auto",
    subsamplingRate=0.8,
)

# Build pipeline (no StringIndexer needed)
pipeline = Pipeline(stages=[vector_assembler, rf])

print(f"Pipeline stages: {len(pipeline.getStages())}")
for i, stage in enumerate(pipeline.getStages(), 1):
    print(f"  {i}. {stage.__class__.__name__}")
print(f"Features used: {FEATURE_COLUMNS}")

# ---------------------------------------------------------------------------
# Train/Test Split
# ---------------------------------------------------------------------------
print("\n" + "=" * 80)
print("Train/Test Split (80/20)...")
print("=" * 80)

train_df, test_df = df_clean.randomSplit([0.8, 0.2], seed=42)
print(f"Training set records: {train_df.count()}")
print(f"Test set records: {test_df.count()}")

# ---------------------------------------------------------------------------
# Train the model
# ---------------------------------------------------------------------------
print("\n" + "=" * 80)
print("Training Random Forest Model...")
print("=" * 80)

model = pipeline.fit(train_df)
print("Model training completed")

# ---------------------------------------------------------------------------
# Make predictions on test set
# ---------------------------------------------------------------------------
print("\n" + "=" * 80)
print("Evaluating Model on Test Set...")
print("=" * 80)

predictions = model.transform(test_df)

# Show sample predictions
print("\nSample Predictions:")
predictions.select(
    LABEL_COLUMN,
    "prediction",
    ((predictions[LABEL_COLUMN] - predictions["prediction"]).alias("error"))
).limit(10).show()

# ---------------------------------------------------------------------------
# Evaluate model
# ---------------------------------------------------------------------------
print("\n" + "=" * 80)
print("Model Evaluation Metrics")
print("=" * 80)

# RMSE (Root Mean Squared Error)
rmse_evaluator = RegressionEvaluator(
    labelCol=LABEL_COLUMN,
    predictionCol="prediction",
    metricName="rmse"
)
rmse = rmse_evaluator.evaluate(predictions)
print(f"RMSE (Root Mean Squared Error): {rmse:.4f}")

# MAE (Mean Absolute Error)
mae_evaluator = RegressionEvaluator(
    labelCol=LABEL_COLUMN,
    predictionCol="prediction",
    metricName="mae"
)
mae = mae_evaluator.evaluate(predictions)
print(f"MAE (Mean Absolute Error): {mae:.4f}")

# R² (Coefficient of Determination)
r2_evaluator = RegressionEvaluator(
    labelCol=LABEL_COLUMN,
    predictionCol="prediction",
    metricName="r2"
)
r2 = r2_evaluator.evaluate(predictions)
print(f"R2 (Coefficient of Determination): {r2:.4f}")

# ---------------------------------------------------------------------------
# Extract and display feature importance
# ---------------------------------------------------------------------------
print("\n" + "=" * 80)
print("Feature Importance")
print("=" * 80)

# Get the trained RandomForestRegressor model from the pipeline
rf_model = model.stages[-1]

# Get feature importance
feature_importance = rf_model.featureImportances.toArray()

# Create feature name mapping
feature_names = FEATURE_COLUMNS

# Create importance list and sort
importance_list = list(zip(feature_names, feature_importance))
importance_list.sort(key=lambda x: x[1], reverse=True)

# Display importance
print(f"\n{'Feature':<30} {'Importance':>15} {'Percentage':>15}")
print("-" * 60)
for feature_name, importance in importance_list:
    percentage = (importance * 100)
    print(f"{feature_name:<30} {importance:>15.6f} {percentage:>14.2f}%")

# ---------------------------------------------------------------------------
# Save the trained model
# ---------------------------------------------------------------------------
print("\n" + "=" * 80)
print("Saving Trained Model...")
print("=" * 80)

# Remove existing model if it exists
import shutil
if os.path.exists(MODEL_OUTPUT_PATH):
    print(f"Removing existing model directory: {MODEL_OUTPUT_PATH}")
    shutil.rmtree(MODEL_OUTPUT_PATH)

# Save the pipeline model (includes preprocessing and RF model)
model.write().overwrite().save(MODEL_OUTPUT_PATH)
print(f"Model saved to: {MODEL_OUTPUT_PATH}")

# ---------------------------------------------------------------------------
# Model Summary and Statistics
# ---------------------------------------------------------------------------
print("\n" + "=" * 80)
print("Model Summary")
print("=" * 80)
print(f"Model Type: Random Forest Regressor")
print(f"Number of Trees: {rf_model.numTrees}")
print(f"Max Depth: {rf_model.maxDepth}")
print(f"Total Trees: {rf_model.trees.__len__()}")
print(f"Training Set Size: {train_df.count()}")
print(f"Test Set Size: {test_df.count()}")
print(f"\nPerformance Metrics:")
print(f"  RMSE: {rmse:.4f}")
print(f"  MAE:  {mae:.4f}")
print(f"  R²:   {r2:.4f}")

# ---------------------------------------------------------------------------
# Next Steps
# ---------------------------------------------------------------------------
print("\n" + "=" * 80)
print("Next Steps")
print("=" * 80)
print("To load and use the model for predictions:")
print("")
print("  from pyspark.ml import PipelineModel")
print(f"  model = PipelineModel.load('{MODEL_OUTPUT_PATH}')")
print("  predictions = model.transform(new_data)")
print("")

spark.stop()
print("Spark session closed")
print("=" * 80)
