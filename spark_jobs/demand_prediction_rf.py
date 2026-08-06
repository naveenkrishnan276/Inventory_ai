"""
Scikit-Learn Random Forest Regression - Demand Prediction Model

Trains a Random Forest regression model to predict product demand using
aggregated streaming data from the retail_aggregations Parquet dataset.

Features:
    - total_units_sold
    - total_revenue
    - avg_units_per_minute
    - transaction_count

Label:
    - total_units_sold (next-window demand proxy)

Output:
    - Trained model saved to: models/demand_rf_model.joblib
"""

import os
import glob
import pandas as pd
from pathlib import Path
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
import s3fs
import boto3
import tempfile
import joblib

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
INPUT_PATH = "s3://inventory-ai-data-nkr/retail_aggregations"
MODEL_OUTPUT_PATH = "s3://inventory-ai-models-nkr/demand_rf_model.joblib"

FEATURE_COLUMNS = [
    "total_units_sold",
    "total_revenue",
    "avg_units_per_minute",
    "transaction_count",
]
LABEL_COLUMN = "total_units_sold"

# ---------------------------------------------------------------------------
# Read aggregated streaming data from Parquet
# ---------------------------------------------------------------------------
print("=" * 80)
print("Reading aggregated data from Parquet in S3...")
print("=" * 80)

try:
    df = pd.read_parquet(INPUT_PATH, engine="pyarrow")
except Exception as e:
    print(f"Failed to read parquet from S3 {INPUT_PATH}: {e}")
    print("Ensure streaming job has been running and produced output.")
    exit(1)
print(f"Loaded {len(df)} records.")

# Clean data
df = df.dropna(subset=FEATURE_COLUMNS + [LABEL_COLUMN])

if len(df) == 0:
    print("No valid rows after dropping nulls.")
    exit(1)

X = df[FEATURE_COLUMNS]
y = df[LABEL_COLUMN]

# Train Test Split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

print("\n" + "=" * 80)
print("Training Scikit-Learn Random Forest Model...")
print("=" * 80)

rf = RandomForestRegressor(n_estimators=50, max_depth=10, random_state=42)
rf.fit(X_train, y_train)

# Evaluate
predictions = rf.predict(X_test)
rmse = mean_squared_error(y_test, predictions) ** 0.5
r2 = r2_score(y_test, predictions)

print(f"Root Mean Squared Error (RMSE) on test data = {rmse}")
print(f"R-squared (R2) on test data = {r2}")

importances = list(zip(FEATURE_COLUMNS, rf.feature_importances_))
importances.sort(key=lambda x: x[1], reverse=True)
print("\nFeature Importances:")
for f, imp in importances:
    print(f"  {f}: {imp:.4f}")

# Save Model to local temp, then upload to S3
with tempfile.NamedTemporaryFile(delete=False, suffix=".joblib") as tmp:
    temp_path = tmp.name
joblib.dump(rf, temp_path)

print("\nUploading model to S3...")
s3 = boto3.client("s3")
bucket_name = MODEL_OUTPUT_PATH.replace("s3://", "").split("/")[0]
object_name = "/".join(MODEL_OUTPUT_PATH.replace("s3://", "").split("/")[1:])
s3.upload_file(temp_path, bucket_name, object_name)
os.remove(temp_path)

print(f"\nModel saved to {MODEL_OUTPUT_PATH}")
