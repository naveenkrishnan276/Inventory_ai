from fastapi import Depends, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from .auth import verify_api_token
from .scheduler import configure_scheduler
from .schemas import (
    AnalyticsResponse,
    DemandPredictionsResponse,
    HomeSummary,
    ReorderListResponse,
    RetrainResponse,
    RetrainStatus,
    UpdateStockRequest,
    UpdateStockResponse,
)
from .services import (
    get_analytics_trends,
    get_demand_predictions,
    get_home_summary,
    get_reorder_list,
    trigger_retrain_async,
    update_inventory_stock,
    run_retrain_job,
)
from .state import ensure_state_files, read_retrain_status


app = FastAPI(title="Inventory AI Backend", version="0.1.0")
scheduler = None

# Add CORS middleware to allow frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update with specific frontend URL if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    global scheduler
    ensure_state_files()
    scheduler = configure_scheduler(run_retrain_job)


@app.on_event("shutdown")
def on_shutdown():
    global scheduler
    if scheduler is not None:
        scheduler.shutdown(wait=False)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/home/summary", response_model=HomeSummary)
def home_summary(_: None = Depends(verify_api_token)):
    return get_home_summary()


@app.get("/api/demand/predictions", response_model=DemandPredictionsResponse)
def demand_predictions(
    limit: int = Query(default=200, ge=1, le=2000),
    _: None = Depends(verify_api_token),
):
    return {"rows": get_demand_predictions(limit=limit)}


@app.post("/api/demand/retrain", response_model=RetrainResponse)
def demand_retrain(_: None = Depends(verify_api_token)):
    started = trigger_retrain_async()
    if not started:
        return {"status": "running", "message": "Retraining already in progress"}
    return {"status": "accepted", "message": "Retraining started"}


@app.get("/api/demand/retrain-status", response_model=RetrainStatus)
def demand_retrain_status(_: None = Depends(verify_api_token)):
    return read_retrain_status()


@app.get("/api/analytics/trends", response_model=AnalyticsResponse)
def analytics_trends(
    range_days: int = Query(default=7, ge=3, le=30),
    _: None = Depends(verify_api_token),
):
    return get_analytics_trends(range_days=range_days)


@app.get("/api/reorder/list", response_model=ReorderListResponse)
def reorder_list(_: None = Depends(verify_api_token)):
    return {"rows": get_reorder_list()}


@app.post("/api/inventory/update-stock", response_model=UpdateStockResponse)
def inventory_update_stock(request: UpdateStockRequest, _: None = Depends(verify_api_token)):
    existed = update_inventory_stock(
        store_id=request.store_id,
        product_id=request.product_id,
        current_stock=request.current_stock,
    )
    if existed:
        return {"status": "updated", "message": "Stock updated"}
    return {"status": "created", "message": "New inventory row added"}
