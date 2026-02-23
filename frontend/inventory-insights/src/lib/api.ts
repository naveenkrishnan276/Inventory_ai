import type {
  HomeSummary,
  DemandPredictionsResponse,
  RetrainStatusResponse,
  AnalyticsTrends,
  ReorderListResponse,
  StockUpdatePayload,
} from "./types";
import { mockHomeSummary, mockDemandPredictions, mockRetrainStatus, mockAnalyticsTrends, mockReorderList } from "./mock-data";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const API_TOKEN = import.meta.env.VITE_API_TOKEN ?? "dev-token";

const headers: Record<string, string> = {
  "Content-Type": "application/json",
  "x-api-token": API_TOKEN,
};

type BackendDemandRow = {
  timestamp: string;
  store_id: string;
  product_id: string;
  predicted_daily_demand: number;
  actual_sales: number;
};

type BackendDemandResponse = {
  rows: BackendDemandRow[];
};

type BackendRetrainStatus = {
  status: "idle" | "running" | "success" | "failed";
  last_run: string | null;
  model_version: string;
  rmse: number | null;
  r2: number | null;
};

type BackendAnalyticsPoint = { date: string; value: number };
type BackendAnalyticsResponse = {
  sales_rate: BackendAnalyticsPoint[];
  demand_rate: BackendAnalyticsPoint[];
  reorder_rate: BackendAnalyticsPoint[];
  risk_distribution: { low: number; medium: number; high: number; critical: number };
};

type BackendReorderRow = {
  store_id: string;
  product_id: string;
  risk_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  recommended_reorder_quantity: number;
  seller_name: string;
  seller_contact: string;
  auto_confirm_eligible: boolean;
  status: "pending" | "created" | "confirmed" | "failed";
  last_reorder_date: string | null;
  current_stock: number;
  predicted_daily_demand: number;
  days_of_cover: number;
};

type BackendReorderResponse = {
  rows: BackendReorderRow[];
};

function toTrend(points: BackendAnalyticsPoint[]) {
  return points.map((point) => ({ date: point.date, value: point.value }));
}

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  try {
    const res = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers: { ...headers, ...options?.headers },
    });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  } catch (error) {
    console.warn(`API call failed for ${path}, using mock data`, error);
    throw error;
  }
}

// ===== Home =====
export async function fetchHomeSummary(): Promise<HomeSummary> {
  try {
    return await fetchApi<HomeSummary>("/api/home/summary");
  } catch {
    return mockHomeSummary;
  }
}

// ===== Demand =====
export async function fetchDemandPredictions(limit = 200): Promise<DemandPredictionsResponse> {
  try {
    const backendData = await fetchApi<BackendDemandResponse>(`/api/demand/predictions?limit=${limit}`);
    const predictions = backendData.rows.map((row) => ({
      store_id: row.store_id,
      product_id: row.product_id,
      date: row.timestamp.split("T")[0],
      predicted_demand: row.predicted_daily_demand,
      actual_demand: row.actual_sales,
      confidence: 0.85,
    }));
    return {
      predictions,
      total: predictions.length,
    };
  } catch {
    return mockDemandPredictions;
  }
}

export async function triggerRetrain(): Promise<{ message: string }> {
  return fetchApi("/api/demand/retrain", { method: "POST" });
}

export async function fetchRetrainStatus(): Promise<RetrainStatusResponse> {
  try {
    const status = await fetchApi<BackendRetrainStatus>("/api/demand/retrain-status");
    return {
      ...status,
      status: status.status === "success" ? "completed" : status.status,
    };
  } catch {
    return mockRetrainStatus;
  }
}

// ===== Analytics =====
export async function fetchAnalyticsTrends(rangeDays = 7): Promise<AnalyticsTrends> {
  try {
    const backendData = await fetchApi<BackendAnalyticsResponse>(`/api/analytics/trends?range_days=${rangeDays}`);
    const salesTrend = toTrend(backendData.sales_rate);
    const demandTrend = toTrend(backendData.demand_rate);
    const reorderTrend = backendData.reorder_rate.map((point) => ({ date: point.date, count: point.value }));

    const avgDailySales = salesTrend.length
      ? salesTrend.reduce((sum, point) => sum + point.value, 0) / salesTrend.length
      : 0;
    const avgDailyDemand = demandTrend.length
      ? demandTrend.reduce((sum, point) => sum + point.value, 0) / demandTrend.length
      : 0;
    const reorderEventsCount = reorderTrend.reduce((sum, point) => sum + point.count, 0);

    const demandRows = await fetchDemandPredictions(200);
    const productMap = new Map<string, { product_id: string; store_id: string; values: number[] }>();
    for (const prediction of demandRows.predictions) {
      const key = `${prediction.store_id}:${prediction.product_id}`;
      const existing = productMap.get(key);
      if (existing) {
        existing.values.push(prediction.actual_demand ?? prediction.predicted_demand);
      } else {
        productMap.set(key, {
          product_id: prediction.product_id,
          store_id: prediction.store_id,
          values: [prediction.actual_demand ?? prediction.predicted_demand],
        });
      }
    }

    const topMovers = Array.from(productMap.values())
      .map((item) => {
        const avg = item.values.reduce((sum, value) => sum + value, 0) / item.values.length;
        return {
          product_id: item.product_id,
          store_id: item.store_id,
          avg_daily_sales: avg,
          trend: "stable" as const,
        };
      })
      .sort((a, b) => b.avg_daily_sales - a.avg_daily_sales)
      .slice(0, 10);

    return {
      sales_trend: salesTrend,
      demand_trend: demandTrend,
      reorder_trend: reorderTrend,
      risk_distribution: {
        LOW: backendData.risk_distribution.low,
        MEDIUM: backendData.risk_distribution.medium,
        HIGH: backendData.risk_distribution.high,
        CRITICAL: backendData.risk_distribution.critical,
      },
      avg_daily_sales: avgDailySales,
      avg_daily_demand: avgDailyDemand,
      reorder_events_count: reorderEventsCount,
      critical_sku_count: backendData.risk_distribution.critical,
      top_movers: topMovers,
    };
  } catch {
    return mockAnalyticsTrends;
  }
}

// ===== Reorder =====
export async function fetchReorderList(): Promise<ReorderListResponse> {
  try {
    const backendData = await fetchApi<BackendReorderResponse>("/api/reorder/list");
    return {
      items: backendData.rows,
    };
  } catch {
    return mockReorderList;
  }
}

// ===== Stock Update =====
export async function updateStock(payload: StockUpdatePayload): Promise<{ success: boolean }> {
  const response = await fetchApi<{ status: string }>("/api/inventory/update-stock", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return { success: response.status === "updated" || response.status === "created" };
}
