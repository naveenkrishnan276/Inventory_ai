import type {
  HomeSummary,
  DemandPredictionsResponse,
  RetrainStatusResponse,
  AnalyticsTrends,
  ReorderListResponse,
} from "./types";

export const mockHomeSummary: HomeSummary = {
  total_inventory_units: 48520,
  at_risk_products: 23,
  today_sales_revenue: 12480.5,
  stockout_risk_percent: 8.4,
  inventory_health: [
    { store_id: "S001", product_id: "P101", current_stock: 320, predicted_daily_demand: 45, days_of_cover: 7.1, risk_level: "LOW" },
    { store_id: "S001", product_id: "P102", current_stock: 50, predicted_daily_demand: 30, days_of_cover: 1.7, risk_level: "CRITICAL" },
    { store_id: "S002", product_id: "P103", current_stock: 180, predicted_daily_demand: 25, days_of_cover: 7.2, risk_level: "LOW" },
    { store_id: "S002", product_id: "P104", current_stock: 60, predicted_daily_demand: 20, days_of_cover: 3.0, risk_level: "HIGH" },
    { store_id: "S003", product_id: "P105", current_stock: 90, predicted_daily_demand: 18, days_of_cover: 5.0, risk_level: "MEDIUM" },
    { store_id: "S003", product_id: "P106", current_stock: 15, predicted_daily_demand: 22, days_of_cover: 0.7, risk_level: "CRITICAL" },
    { store_id: "S004", product_id: "P107", current_stock: 400, predicted_daily_demand: 50, days_of_cover: 8.0, risk_level: "LOW" },
    { store_id: "S004", product_id: "P108", current_stock: 75, predicted_daily_demand: 28, days_of_cover: 2.7, risk_level: "HIGH" },
    { store_id: "S005", product_id: "P109", current_stock: 200, predicted_daily_demand: 35, days_of_cover: 5.7, risk_level: "MEDIUM" },
    { store_id: "S005", product_id: "P110", current_stock: 25, predicted_daily_demand: 40, days_of_cover: 0.6, risk_level: "CRITICAL" },
  ],
  risk_distribution: { LOW: 45, MEDIUM: 22, HIGH: 18, CRITICAL: 15 },
  top_at_risk: [
    { store_id: "S005", product_id: "P110", days_of_cover: 0.6, risk_level: "CRITICAL" },
    { store_id: "S003", product_id: "P106", days_of_cover: 0.7, risk_level: "CRITICAL" },
    { store_id: "S001", product_id: "P102", days_of_cover: 1.7, risk_level: "CRITICAL" },
    { store_id: "S004", product_id: "P108", days_of_cover: 2.7, risk_level: "HIGH" },
    { store_id: "S002", product_id: "P104", days_of_cover: 3.0, risk_level: "HIGH" },
  ],
};

const generateDemandData = () => {
  const predictions = [];
  const stores = ["S001", "S002", "S003", "S004", "S005"];
  const products = ["P101", "P102", "P103", "P104", "P105"];
  for (let i = 0; i < 30; i++) {
    const date = new Date();
    date.setDate(date.getDate() - (29 - i));
    for (const store of stores) {
      for (const product of products) {
        const predicted = Math.round(20 + Math.random() * 60);
        predictions.push({
          store_id: store,
          product_id: product,
          date: date.toISOString().split("T")[0],
          predicted_demand: predicted,
          actual_demand: i < 25 ? Math.round(predicted * (0.8 + Math.random() * 0.4)) : null,
          confidence: 0.7 + Math.random() * 0.25,
        });
      }
    }
  }
  return predictions;
};

export const mockDemandPredictions: DemandPredictionsResponse = {
  predictions: generateDemandData(),
  total: 750,
};

export const mockRetrainStatus: RetrainStatusResponse = {
  status: "completed",
  last_run: new Date(Date.now() - 3600000).toISOString(),
  model_version: "v2.4.1",
  rmse: 4.23,
  r2: 0.912,
};

const generateTrend = (days: number, base: number, variance: number) => {
  return Array.from({ length: days }, (_, i) => {
    const date = new Date();
    date.setDate(date.getDate() - (days - 1 - i));
    return { date: date.toISOString().split("T")[0], value: Math.round(base + (Math.random() - 0.5) * variance) };
  });
};

export const mockAnalyticsTrends: AnalyticsTrends = {
  sales_trend: generateTrend(30, 350, 100),
  demand_trend: generateTrend(30, 400, 120),
  reorder_trend: Array.from({ length: 30 }, (_, i) => {
    const date = new Date();
    date.setDate(date.getDate() - (29 - i));
    return { date: date.toISOString().split("T")[0], count: Math.floor(Math.random() * 8) };
  }),
  risk_distribution: { LOW: 45, MEDIUM: 22, HIGH: 18, CRITICAL: 15 },
  avg_daily_sales: 345.8,
  avg_daily_demand: 412.3,
  reorder_events_count: 42,
  critical_sku_count: 15,
  top_movers: [
    { product_id: "P102", store_id: "S001", avg_daily_sales: 78.5, trend: "up" },
    { product_id: "P110", store_id: "S005", avg_daily_sales: 65.2, trend: "up" },
    { product_id: "P105", store_id: "S003", avg_daily_sales: 52.1, trend: "stable" },
    { product_id: "P107", store_id: "S004", avg_daily_sales: 48.9, trend: "down" },
    { product_id: "P103", store_id: "S002", avg_daily_sales: 44.3, trend: "up" },
  ],
};

export const mockReorderList: ReorderListResponse = {
  items: [
    { store_id: "S005", product_id: "P110", risk_level: "CRITICAL", recommended_reorder_quantity: 500, seller_name: "Global Supplies Co", seller_contact: "orders@globalsupplies.com", auto_confirm_eligible: true, status: "pending", last_reorder_date: null, current_stock: 25, predicted_daily_demand: 40, days_of_cover: 0.6 },
    { store_id: "S003", product_id: "P106", risk_level: "CRITICAL", recommended_reorder_quantity: 300, seller_name: "FastTrack Dist.", seller_contact: "sales@fasttrack.com", auto_confirm_eligible: true, status: "pending", last_reorder_date: "2025-02-10", current_stock: 15, predicted_daily_demand: 22, days_of_cover: 0.7 },
    { store_id: "S001", product_id: "P102", risk_level: "CRITICAL", recommended_reorder_quantity: 400, seller_name: "MegaParts Inc", seller_contact: "bulk@megaparts.com", auto_confirm_eligible: false, status: "pending", last_reorder_date: "2025-02-15", current_stock: 50, predicted_daily_demand: 30, days_of_cover: 1.7 },
    { store_id: "S004", product_id: "P108", risk_level: "HIGH", recommended_reorder_quantity: 250, seller_name: "QuickShip LLC", seller_contact: "info@quickship.com", auto_confirm_eligible: true, status: "created", last_reorder_date: "2025-02-18", current_stock: 75, predicted_daily_demand: 28, days_of_cover: 2.7 },
    { store_id: "S002", product_id: "P104", risk_level: "HIGH", recommended_reorder_quantity: 200, seller_name: "PrimeGoods", seller_contact: "orders@primegoods.com", auto_confirm_eligible: false, status: "pending", last_reorder_date: null, current_stock: 60, predicted_daily_demand: 20, days_of_cover: 3.0 },
    { store_id: "S003", product_id: "P105", risk_level: "MEDIUM", recommended_reorder_quantity: 150, seller_name: "ValueWare", seller_contact: "sales@valueware.com", auto_confirm_eligible: false, status: "confirmed", last_reorder_date: "2025-02-20", current_stock: 90, predicted_daily_demand: 18, days_of_cover: 5.0 },
    { store_id: "S001", product_id: "P101", risk_level: "LOW", recommended_reorder_quantity: 0, seller_name: "EverStock", seller_contact: "contact@everstock.com", auto_confirm_eligible: false, status: "confirmed", last_reorder_date: "2025-02-22", current_stock: 320, predicted_daily_demand: 45, days_of_cover: 7.1 },
  ],
};
