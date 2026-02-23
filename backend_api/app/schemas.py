from pydantic import BaseModel, Field


class HomeSummary(BaseModel):
    total_inventory_units: int
    at_risk_products: int
    today_sales_revenue: float
    stockout_risk_percent: float
    last_refresh: str
    model_version: str
    inventory_health: list["InventoryHealthRow"]
    risk_distribution: "RiskDistribution"
    top_at_risk: list["AtRiskProduct"]


class InventoryHealthRow(BaseModel):
    store_id: str
    product_id: str
    current_stock: int
    predicted_daily_demand: float
    days_of_cover: float
    risk_level: str


class RiskDistribution(BaseModel):
    LOW: int
    MEDIUM: int
    HIGH: int
    CRITICAL: int


class AtRiskProduct(BaseModel):
    store_id: str
    product_id: str
    days_of_cover: float
    risk_level: str


class DemandPredictionRow(BaseModel):
    timestamp: str
    store_id: str
    product_id: str
    predicted_daily_demand: float
    actual_sales: float


class DemandPredictionsResponse(BaseModel):
    rows: list[DemandPredictionRow]


class RetrainResponse(BaseModel):
    status: str
    message: str


class RetrainStatus(BaseModel):
    status: str
    last_run: str | None
    model_version: str
    rmse: float | None
    r2: float | None


class AnalyticsPoint(BaseModel):
    date: str
    value: float


class AnalyticsRiskDistribution(BaseModel):
    low: int
    medium: int
    high: int
    critical: int


class AnalyticsResponse(BaseModel):
    sales_rate: list[AnalyticsPoint]
    demand_rate: list[AnalyticsPoint]
    reorder_rate: list[AnalyticsPoint]
    risk_distribution: AnalyticsRiskDistribution


class ReorderRow(BaseModel):
    store_id: str
    product_id: str
    risk_level: str
    recommended_reorder_quantity: int
    seller_name: str
    seller_contact: str
    action: str
    auto_confirm_eligible: bool
    status: str
    last_reorder_date: str | None
    current_stock: int
    predicted_daily_demand: float
    days_of_cover: float


class ReorderListResponse(BaseModel):
    rows: list[ReorderRow]


class UpdateStockRequest(BaseModel):
    store_id: str = Field(min_length=1)
    product_id: str = Field(min_length=1)
    current_stock: int = Field(ge=0)


class UpdateStockResponse(BaseModel):
    status: str
    message: str
