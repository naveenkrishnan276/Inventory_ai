# Inventory AI FastAPI Backend (MVP)

This backend gives your frontend ready-to-use APIs for Home, Demand, Analytics, Reorder, and manual stock updates.

## Features

- Token-protected API endpoints for dashboard tabs
- Daily retraining scheduler at **1:00 AM IST**
- Manual retrain trigger endpoint
- Reorder list with seller details and auto-confirm eligibility
- Stock update endpoint (writes to `data/current_inventory.csv`)

## Project Structure

- `backend_api/app/main.py` — FastAPI app and routes
- `backend_api/app/services.py` — core business logic
- `backend_api/app/scheduler.py` — APScheduler daily job
- `backend_api/app/state.py` — retrain status storage
- `backend_api/app/schemas.py` — request/response contracts

## Run Locally

```bash
cd backend_api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export API_TOKEN=dev-token
uvicorn app.main:app --host 0.0.0.0 --port 8081 --reload
```

Health check:

```bash
curl http://localhost:8000/health
```

Authenticated call example:

```bash
curl -H "x-api-token: dev-token" http://localhost:8000/api/home/summary
```

## API Contracts

### `GET /api/home/summary`

```json
{
  "total_inventory_units": 12345,
  "at_risk_products": 7,
  "today_sales_revenue": 456789.12,
  "stockout_risk_percent": 13.46,
  "last_refresh": "2026-02-23T10:11:12.123456+00:00",
  "model_version": "demand_rf_model_20260223_011501"
}
```

### `GET /api/demand/predictions?limit=200`

```json
{
  "rows": [
    {
      "timestamp": "2026-02-23T10:11:12.123456+00:00",
      "store_id": "STORE_001",
      "product_id": "PROD_006",
      "predicted_daily_demand": 88.2,
      "actual_sales": 79.4
    }
  ]
}
```

### `POST /api/demand/retrain`

```json
{
  "status": "accepted",
  "message": "Retraining started"
}
```

### `GET /api/demand/retrain-status`

```json
{
  "status": "success",
  "last_run": "2026-02-23T01:00:05.000000+00:00",
  "model_version": "demand_rf_model_20260223_010005",
  "rmse": 1.2345,
  "r2": 0.9876
}
```

### `GET /api/analytics/trends?range_days=7`

```json
{
  "sales_rate": [{ "date": "2026-02-17", "value": 1000.0 }],
  "demand_rate": [{ "date": "2026-02-17", "value": 950.0 }],
  "reorder_rate": [{ "date": "2026-02-17", "value": 12.0 }],
  "risk_distribution": { "low": 20, "medium": 12, "high": 4, "critical": 2 }
}
```

### `GET /api/reorder/list`

```json
{
  "rows": [
    {
      "store_id": "STORE_004",
      "product_id": "PROD_017",
      "risk_level": "HIGH",
      "recommended_reorder_quantity": 120,
      "seller_name": "SouthMart Wholesale",
      "seller_contact": "+91-9000011111",
      "action": "CREATE_DRAFT_PO",
      "auto_confirm_eligible": false,
      "status": "pending"
    }
  ]
}
```

### `POST /api/inventory/update-stock`

Request:

```json
{
  "store_id": "STORE_001",
  "product_id": "PROD_006",
  "current_stock": 140
}
```

Response:

```json
{
  "status": "updated",
  "message": "Stock updated"
}
```

## Frontend Integration Notes

- Send `x-api-token` header in every `/api/*` request.
- Set frontend env:
  - `NEXT_PUBLIC_API_BASE_URL=http://<backend-host>:8000`
  - `NEXT_PUBLIC_API_TOKEN=dev-token` (for dev only)
