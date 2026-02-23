import csv
import hashlib
import re
import subprocess
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .state import read_retrain_status, utc_now_iso, write_retrain_status


ROOT = Path(__file__).resolve().parents[2]
INVENTORY_PATH = ROOT / "data" / "current_inventory.csv"
SELLER_PATH = ROOT / "data" / "seller_master.csv"
TRAIN_SCRIPT = ROOT / "spark_jobs" / "demand_prediction_rf.py"

RETRAIN_LOCK = threading.Lock()


def _stable_float(key: str, min_val: float, max_val: float) -> float:
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    value = int(digest[:8], 16) / 0xFFFFFFFF
    return min_val + (max_val - min_val) * value


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


def _predicted_daily_demand(store_id: str, product_id: str) -> float:
    return round(_stable_float(f"{store_id}:{product_id}:demand", 20.0, 180.0), 2)


def _actual_daily_sales(store_id: str, product_id: str, predicted: float) -> float:
    factor = _stable_float(f"{store_id}:{product_id}:actual", 0.75, 1.1)
    return round(predicted * factor, 2)


def _risk_level(days_of_cover: float) -> str:
    if days_of_cover <= 1:
        return "CRITICAL"
    if days_of_cover <= 2:
        return "HIGH"
    if days_of_cover <= 4:
        return "MEDIUM"
    return "LOW"


def _reorder_quantity(stock: int, lead_time_days: int, predicted_daily_demand: float) -> int:
    buffer_days = 2
    target_stock = int((lead_time_days + buffer_days) * predicted_daily_demand)
    return max(0, target_stock - stock)


def compute_inventory_rows() -> list[dict]:
    rows = _load_inventory()
    enriched: list[dict] = []

    for row in rows:
        predicted = _predicted_daily_demand(row["store_id"], row["product_id"])
        actual = _actual_daily_sales(row["store_id"], row["product_id"], predicted)
        days_of_cover = round(row["current_stock"] / max(predicted, 1), 2)
        risk_level = _risk_level(days_of_cover)
        reorder_qty = _reorder_quantity(row["current_stock"], row["lead_time_days"], predicted)

        enriched.append(
            {
                **row,
                "predicted_daily_demand": predicted,
                "actual_sales": actual,
                "days_of_cover": days_of_cover,
                "risk_level": risk_level,
                "recommended_reorder_quantity": reorder_qty,
            }
        )

    return enriched


def get_home_summary() -> dict:
    data = compute_inventory_rows()
    total_inventory_units = sum(item["current_stock"] for item in data)
    at_risk = sum(1 for item in data if item["risk_level"] in {"HIGH", "CRITICAL"})
    stockout_risk_percent = round((at_risk / max(len(data), 1)) * 100, 2)
    today_sales_revenue = round(sum(item["actual_sales"] * 42.0 for item in data), 2)

    retrain = read_retrain_status()

    return {
        "total_inventory_units": total_inventory_units,
        "at_risk_products": at_risk,
        "today_sales_revenue": today_sales_revenue,
        "stockout_risk_percent": stockout_risk_percent,
        "last_refresh": utc_now_iso(),
        "model_version": retrain.get("model_version", "demand_rf_model_current"),
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
            ["python3", str(TRAIN_SCRIPT)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=3600,
            check=False,
        )

        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        combined = f"{stdout}\n{stderr}"

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
