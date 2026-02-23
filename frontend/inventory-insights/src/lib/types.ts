// ===== Risk & Status Enums =====
export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type ReorderStatus = "pending" | "created" | "confirmed" | "failed";
export type RetrainStatus = "idle" | "running" | "completed" | "failed";

// ===== Home =====
export interface HomeSummary {
  total_inventory_units: number;
  at_risk_products: number;
  today_sales_revenue: number;
  stockout_risk_percent: number;
  inventory_health: InventoryHealthRow[];
  risk_distribution: RiskDistribution;
  top_at_risk: AtRiskProduct[];
}

export interface InventoryHealthRow {
  store_id: string;
  product_id: string;
  current_stock: number;
  predicted_daily_demand: number;
  days_of_cover: number;
  risk_level: RiskLevel;
}

export interface RiskDistribution {
  LOW: number;
  MEDIUM: number;
  HIGH: number;
  CRITICAL: number;
}

export interface AtRiskProduct {
  store_id: string;
  product_id: string;
  days_of_cover: number;
  risk_level: RiskLevel;
}

// ===== Demand =====
export interface DemandPrediction {
  store_id: string;
  product_id: string;
  date: string;
  predicted_demand: number;
  actual_demand: number | null;
  confidence: number;
}

export interface DemandPredictionsResponse {
  predictions: DemandPrediction[];
  total: number;
}

export interface RetrainStatusResponse {
  status: RetrainStatus;
  last_run: string | null;
  model_version: string;
  rmse: number | null;
  r2: number | null;
}

// ===== Analytics =====
export interface AnalyticsTrends {
  sales_trend: TrendPoint[];
  demand_trend: TrendPoint[];
  reorder_trend: ReorderTrendPoint[];
  risk_distribution: RiskDistribution;
  avg_daily_sales: number;
  avg_daily_demand: number;
  reorder_events_count: number;
  critical_sku_count: number;
  top_movers: TopMover[];
}

export interface TrendPoint {
  date: string;
  value: number;
}

export interface ReorderTrendPoint {
  date: string;
  count: number;
}

export interface TopMover {
  product_id: string;
  store_id: string;
  avg_daily_sales: number;
  trend: "up" | "down" | "stable";
}

// ===== Reorder =====
export interface ReorderItem {
  store_id: string;
  product_id: string;
  risk_level: RiskLevel;
  recommended_reorder_quantity: number;
  seller_name: string;
  seller_contact: string;
  auto_confirm_eligible: boolean;
  status: ReorderStatus;
  last_reorder_date: string | null;
  current_stock: number;
  predicted_daily_demand: number;
  days_of_cover: number;
}

export interface ReorderListResponse {
  items: ReorderItem[];
}

// ===== Stock Update =====
export interface StockUpdatePayload {
  store_id: string;
  product_id: string;
  current_stock: number;
}

// ===== Filters =====
export interface GlobalFilters {
  store_id: string;
  product_id: string;
  date_range: [Date | null, Date | null];
  risk_level: RiskLevel | "ALL";
}
