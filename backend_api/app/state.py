import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = ROOT / "backend_api" / "state"
RETRAIN_STATUS_PATH = STATE_DIR / "retrain_status.json"


DEFAULT_RETRAIN_STATUS = {
    "status": "idle",
    "last_run": None,
    "model_version": "demand_rf_model_current",
    "rmse": None,
    "r2": None,
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_state_files() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if not RETRAIN_STATUS_PATH.exists():
        write_retrain_status(DEFAULT_RETRAIN_STATUS)


def read_retrain_status() -> dict:
    ensure_state_files()
    with RETRAIN_STATUS_PATH.open("r", encoding="utf-8") as fp:
        return json.load(fp)


def write_retrain_status(payload: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with RETRAIN_STATUS_PATH.open("w", encoding="utf-8") as fp:
        json.dump(payload, fp, indent=2)
