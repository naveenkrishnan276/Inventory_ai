import csv
import hashlib
import re
import subprocess
import threading
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .state import read_retrain_status, utc_now_iso, write_retrain_status


ROOT = Path(__file__).resolve().parents[2]
INVENTORY_PATH = ROOT / "data" / "current_inventory.csv"
SELLER_PATH = ROOT / "data" / "seller_master.csv"
TRAIN_SCRIPT = ROOT / "spark_jobs" / "demand_prediction_rf.py"

RETRAIN_LOCK = threading.Lock()

# --- NEW LOGIC: PYSPARK INTEGRATION ---
import pandas as pd
from pyspark.sql import SparkSession
from pyspark.ml import PipelineModel
from pyspark.sql.functions import max as sql_max, lit

_spark_session = None
_rf_model = None
_spark_lock = threading.Lock()

def _get_spark():
    global _spark_session, _rf_model
    if _spark_session is None:
        with _spark_lock:
            if _spark_session is None:
                try:
                    import os, sys
                    HADOOP_HOME = str(ROOT / "hadoop")
                    os.environ["HADOOP_HOME"] = HADOOP_HOME
                    os.environ["hadoop.home.dir"] = HADOOP_HOME
                    os.environ["PATH"] = os.path.join(HADOOP_HOME, "bin") + os.pathsep + os.environ.get("PATH", "")
                    os.environ["PYSPARK_PYTHON"] = sys.executable
                    os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
                    os.environ["PYSPARK_PIN_THREAD"] = "true"
                except Exception:
                    pass
                
                _spark_session = (
                    SparkSession.builder
                    .appName("FastAPIBackend")
                    .master("local[*]")
                    .config("spark.sql.shuffle.partitions", "1")
                    .config("spark.driver.port", "50123")
                    .config("spark.blockManager.port", "50124")
                    .config("spark.ui.port", "4041")
                    .config("spark.python.worker.reuse", "true")
                    .config("spark.python.use.daemon", "false")
                    .config("spark.sql.execution.arrow.pyspark.enabled", "false")
                    .getOrCreate()
                )
                _spark_session.sparkContext.setLogLevel("WARN")
                
                model_path = str(ROOT / "models" / "demand_rf_model")
                try:
                    _rf_model = PipelineModel.load(model_path)
                except Exception as e:
                    print(f"Failed to load RF model: {e}")
                    _rf_model = None
    return _spark_session, _rf_model

def _load_inventory() -> list[dict]:
    rows: list[dict] = []
    with INVENTORY_PATH.open("r", encoding="utf-8") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            rows.append(
                {
                    "store_id": row["store_id"],
                    "product_id": row["product_id"],
                    "current_stock": int(row["current_stock"]),
                    "lead_time_days": int(row["lead_time_days"]),
                }
            )
    return rows

def _load_sellers() -> dict[tuple[str, str], dict]:
    if not SELLER_PATH.exists():
        return {}

    sellers: dict[tuple[str, str], dict] = {}
    with SELLER_PATH.open("r", encoding="utf-8") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            sellers[(row["store_id"], row["product_id"])] = row
    return sellers

def compute_inventory_rows() -> list[dict]:
    rows = _load_inventory()
    RETAIL_AGGREGATIONS_PATH = "s3://inventory-ai-data-nkr/retail_aggregations"
    
    import pandas as pd
    import os
    
    try:
        # Read the entire Hive-partitioned Parquet dataset in a single call.
        # Pandas + pyarrow handles store_id=X/product_id=Y partitioning
        # natively, which is orders of magnitude faster than reading each
        # of the thousands of small files individually.
        if RETAIL_AGGREGATIONS_PATH.exists():
            demand_df = pd.read_parquet(
                str(RETAIL_AGGREGATIONS_PATH),
                engine="pyarrow",
            )
        else:
            demand_df = pd.DataFrame()
        
        if not demand_df.empty:
            agg_cols = {
                'total_units_sold': 'max',
                'total_revenue': 'max',
                'avg_units_per_minute': 'max',
                'transaction_count': 'max'
            }
            if 'prediction' in demand_df.columns:
                agg_cols['prediction'] = 'max'
                
            demand_agg = demand_df.groupby(['store_id', 'product_id']).agg(agg_cols).reset_index()
            
            inventory_df = pd.DataFrame(rows)
            joined_df = pd.merge(inventory_df, demand_agg, on=['store_id', 'product_id'], how='left')
            
            import joblib
            import boto3
            import tempfile
            
            MODEL_PATH = "s3://inventory-ai-models-nkr/demand_rf_model.joblib"
            
            fill_cols = {
                'total_units_sold': 0, 'total_revenue': 0.0, 
                'avg_units_per_minute': 0.0, 'transaction_count': 0
            }
            joined_df.fillna(fill_cols, inplace=True)
            
            features = ['total_units_sold', 'total_revenue', 'avg_units_per_minute', 'transaction_count']
            
            try:
                s3 = boto3.client("s3")
                bucket_name = MODEL_PATH.replace("s3://", "").split("/")[0]
                object_name = "/".join(MODEL_PATH.replace("s3://", "").split("/")[1:])
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=".joblib") as tmp:
                    temp_path = tmp.name
                
                # Check if object exists before downloading
                try:
                    s3.head_object(Bucket=bucket_name, Key=object_name)
                    s3.download_file(bucket_name, object_name, temp_path)
                    rf_model = joblib.load(temp_path)
                    joined_df['prediction'] = rf_model.predict(joined_df[features])
                    os.remove(temp_path)
                except Exception as e:
                    # Model not found or error loading
                    joined_df['prediction'] = 0.0
            except Exception as e:
                print(f"Failed to load/predict with Scikit-Learn model from S3: {e}")
                joined_df['prediction'] = 0.0
                
            results = joined_df.to_dict('records')
        else:
            results = [dict(**r, total_units_sold=0, avg_units_per_minute=0, transaction_count=0, prediction=0.0) for r in rows]
            
    except Exception as e:
        print(f"Error computing real inventory rows: {e}")
        results = [dict(**r, total_units_sold=0, avg_units_per_minute=0, transaction_count=0, prediction=0.0) for r in rows]

    enriched = []
    for item in results:
        if hasattr(item, 'asDict'):
            row_dict = item.asDict()
        else:
            row_dict = item
            
        current_stock = int(row_dict.get("current_stock", 0))
        lead_time_days = int(row_dict.get("lead_time_days", 0))
        
        # ML model prediction (5-min window → daily: ×288)
        model_pred = round(float(row_dict.get("prediction", 0.0)) * 288.0, 2)
        model_pred = max(0.0, model_pred)
        
        # Streaming data metrics from aggregated Parquet
        actual_units = round(float(row_dict.get("total_units_sold", 0)), 2)
        avg_per_min = float(row_dict.get("avg_units_per_minute", 0))
        txn_count = float(row_dict.get("transaction_count", 0))
        
        # Estimate daily demand from streaming data:
        # avg_units_per_minute is already a rate → daily = rate × 60min × 24hr
        streaming_daily = round(avg_per_min * 60.0 * 24.0, 2)
        
        # Use the HIGHER of: model prediction OR streaming estimate
        # This ensures meaningful risk levels even when model predictions are low
        predicted = max(model_pred, streaming_daily)
        
        # Days of cover = how many days current stock can sustain the demand
        days_of_cover = round(current_stock / max(predicted, 1), 2)
        
        # 4-tier risk classification based on days of cover
        if days_of_cover <= 1:
            risk_level = "CRITICAL"
        elif days_of_cover <= 2:
            risk_level = "HIGH"
        elif days_of_cover <= 4:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
            
        # Reorder quantity: enough to cover lead_time + buffer at predicted demand rate
        buffer_days = 2
        target_stock = int((lead_time_days + buffer_days) * predicted)
        reorder_qty = max(0, target_stock - current_stock)

        enriched.append({
            "store_id": row_dict["store_id"],
            "product_id": row_dict["product_id"],
            "current_stock": current_stock,
            "lead_time_days": lead_time_days,
            "predicted_daily_demand": predicted,
            "actual_sales": actual_units,
            "days_of_cover": days_of_cover,
            "risk_level": risk_level,
            "recommended_reorder_quantity": reorder_qty,
        })

    return enriched

def get_home_summary() -> dict:
    data = compute_inventory_rows()
    total_inventory_units = sum(item["current_stock"] for item in data)
    at_risk = sum(1 for item in data if item["risk_level"] in {"HIGH", "CRITICAL"})
    stockout_risk_percent = round((at_risk / max(len(data), 1)) * 100, 2)
    today_sales_revenue = round(sum(item["actual_sales"] * 42.0 for item in data), 2)
    risk_distribution = {
        "LOW": sum(1 for item in data if item["risk_level"] == "LOW"),
        "MEDIUM": sum(1 for item in data if item["risk_level"] == "MEDIUM"),
        "HIGH": sum(1 for item in data if item["risk_level"] == "HIGH"),
        "CRITICAL": sum(1 for item in data if item["risk_level"] == "CRITICAL"),
    }
    top_at_risk = sorted(
        [item for item in data if item["risk_level"] in {"HIGH", "CRITICAL"}],
        key=lambda item: item["days_of_cover"],
    )[:5]

    retrain = read_retrain_status()

    return {
        "total_inventory_units": total_inventory_units,
        "at_risk_products": at_risk,
        "today_sales_revenue": today_sales_revenue,
        "stockout_risk_percent": stockout_risk_percent,
        "last_refresh": utc_now_iso(),
        "model_version": retrain.get("model_version", "demand_rf_model_current"),
        "inventory_health": [
            {
                "store_id": item["store_id"],
                "product_id": item["product_id"],
                "current_stock": item["current_stock"],
                "predicted_daily_demand": item["predicted_daily_demand"],
                "days_of_cover": item["days_of_cover"],
                "risk_level": item["risk_level"],
            }
            for item in data
        ],
        "risk_distribution": risk_distribution,
        "top_at_risk": [
            {
                "store_id": item["store_id"],
                "product_id": item["product_id"],
                "days_of_cover": item["days_of_cover"],
                "risk_level": item["risk_level"],
            }
            for item in top_at_risk
        ],
    }


def get_demand_predictions(limit: int = 200) -> list[dict]:
    now = datetime.now(timezone.utc).isoformat()
    data = compute_inventory_rows()
    rows = []
    for item in data[:limit]:
        rows.append(
            {
                "timestamp": now,
                "store_id": item["store_id"],
                "product_id": item["product_id"],
                "predicted_daily_demand": item["predicted_daily_demand"],
                "actual_sales": item["actual_sales"],
            }
        )
    return rows


def get_analytics_trends(range_days: int = 7) -> dict:
    base_data = compute_inventory_rows()
    total_sales = sum(item["actual_sales"] for item in base_data)
    total_demand = sum(item["predicted_daily_demand"] for item in base_data)
    risk_counts = {
        "low": sum(1 for item in base_data if item["risk_level"] == "LOW"),
        "medium": sum(1 for item in base_data if item["risk_level"] == "MEDIUM"),
        "high": sum(1 for item in base_data if item["risk_level"] == "HIGH"),
        "critical": sum(1 for item in base_data if item["risk_level"] == "CRITICAL"),
    }

    today = datetime.now(timezone.utc).date()
    sales_rate = []
    demand_rate = []
    reorder_rate = []

    for idx in range(range_days - 1, -1, -1):
        date_val = (today - timedelta(days=idx)).isoformat()
        day_mult = 0.88 + (0.02 * (range_days - idx))
        sales_rate.append({"date": date_val, "value": round(total_sales * day_mult, 2)})
        demand_rate.append({"date": date_val, "value": round(total_demand * day_mult, 2)})
        reorder_rate.append(
            {
                "date": date_val,
                "value": round((risk_counts["high"] + risk_counts["critical"]) * day_mult, 2),
            }
        )

    return {
        "sales_rate": sales_rate,
        "demand_rate": demand_rate,
        "reorder_rate": reorder_rate,
        "risk_distribution": risk_counts,
    }


def get_reorder_list() -> list[dict]:
    data = compute_inventory_rows()
    sellers = _load_sellers()

    rows = []
    for item in data:
        if item["risk_level"] not in {"HIGH", "CRITICAL"}:
            continue

        seller = sellers.get((item["store_id"], item["product_id"]), None)
        if seller is None:
            seller_name = "Seller Not Mapped"
            seller_contact = "NA"
            auto_confirm = False
        else:
            seller_name = seller["seller_name"]
            seller_contact = seller["seller_contact"]
            auto_confirm = seller["auto_confirm_eligible"].strip().lower() == "true"

        rows.append(
            {
                "store_id": item["store_id"],
                "product_id": item["product_id"],
                "risk_level": item["risk_level"],
                "recommended_reorder_quantity": item["recommended_reorder_quantity"],
                "seller_name": seller_name,
                "seller_contact": seller_contact,
                "action": "CREATE_DRAFT_PO",
                "auto_confirm_eligible": auto_confirm,
                "status": "pending",
                "last_reorder_date": None,
                "current_stock": item["current_stock"],
                "predicted_daily_demand": item["predicted_daily_demand"],
                "days_of_cover": item["days_of_cover"],
            }
        )

    return rows


def update_inventory_stock(store_id: str, product_id: str, current_stock: int) -> bool:
    rows = _load_inventory()
    updated = False

    for row in rows:
        if row["store_id"] == store_id and row["product_id"] == product_id:
            row["current_stock"] = current_stock
            updated = True
            break

    if not updated:
        rows.append(
            {
                "store_id": store_id,
                "product_id": product_id,
                "current_stock": current_stock,
                "lead_time_days": 3,
            }
        )

    with INVENTORY_PATH.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(
            fp,
            fieldnames=["store_id", "product_id", "current_stock", "lead_time_days"],
        )
        writer.writeheader()
        writer.writerows(rows)

    return updated


def _extract_metric(log_text: str, metric_name: str) -> float | None:
    pattern = rf"{metric_name}.*?:\s*([-+]?\d*\.?\d+)"
    match = re.search(pattern, log_text)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def run_retrain_job() -> None:
    if not RETRAIN_LOCK.acquire(blocking=False):
        return

    try:
        state = read_retrain_status()
        state.update({"status": "running"})
        write_retrain_status(state)

        completed = subprocess.run(
            [sys.executable, str(TRAIN_SCRIPT)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=3600,
            check=False,
        )

        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        combined = f"{stdout}\n{stderr}"

        # Log output for debugging
        print("=== Retrain subprocess output ===")
        print(combined)
        print("=== End retrain output ===")

        if completed.returncode == 0:
            rmse = _extract_metric(combined, "RMSE")
            r2 = _extract_metric(combined, "R²|R2")
            write_retrain_status(
                {
                    "status": "success",
                    "last_run": utc_now_iso(),
                    "model_version": f"demand_rf_model_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
                    "rmse": rmse,
                    "r2": r2,
                }
            )
        else:
            previous = read_retrain_status()
            write_retrain_status(
                {
                    "status": "failed",
                    "last_run": previous.get("last_run"),
                    "model_version": previous.get("model_version", "demand_rf_model_current"),
                    "rmse": previous.get("rmse"),
                    "r2": previous.get("r2"),
                    "error": combined,
                }
            )
    except subprocess.TimeoutExpired:
        previous = read_retrain_status()
        write_retrain_status(
            {
                "status": "failed",
                "last_run": previous.get("last_run"),
                "model_version": previous.get("model_version", "demand_rf_model_current"),
                "rmse": previous.get("rmse"),
                "r2": previous.get("r2"),
                "error": "Timeout expired",
            }
        )
    finally:
        RETRAIN_LOCK.release()
def trigger_retrain_async() -> bool:
    if RETRAIN_LOCK.locked():
        return False

    thread = threading.Thread(target=run_retrain_job, daemon=True)
    thread.start()
    return True
