import type {
  HomeSummary,
  DemandPredictionsResponse,
  RetrainStatusResponse,
  AnalyticsTrends,
  ReorderListResponse,
  StockUpdatePayload,
} from "./types";
import { mockHomeSummary, mockDemandPredictions, mockRetrainStatus, mockAnalyticsTrends, mockReorderList } from "./mock-data";

const API_BASE_URL = "https://your-api-base-url.com";
const API_TOKEN = "your-api-token-here";

const headers: Record<string, string> = {
  "Content-Type": "application/json",
  "x-api-token": API_TOKEN,
};

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
    return await fetchApi<DemandPredictionsResponse>(`/api/demand/predictions?limit=${limit}`);
  } catch {
    return mockDemandPredictions;
  }
}

export async function triggerRetrain(): Promise<{ message: string }> {
  return fetchApi("/api/demand/retrain", { method: "POST" });
}

export async function fetchRetrainStatus(): Promise<RetrainStatusResponse> {
  try {
    return await fetchApi<RetrainStatusResponse>("/api/demand/retrain-status");
  } catch {
    return mockRetrainStatus;
  }
}

// ===== Analytics =====
export async function fetchAnalyticsTrends(rangeDays = 7): Promise<AnalyticsTrends> {
  try {
    return await fetchApi<AnalyticsTrends>(`/api/analytics/trends?range_days=${rangeDays}`);
  } catch {
    return mockAnalyticsTrends;
  }
}

// ===== Reorder =====
export async function fetchReorderList(): Promise<ReorderListResponse> {
  try {
    return await fetchApi<ReorderListResponse>("/api/reorder/list");
  } catch {
    return mockReorderList;
  }
}

// ===== Stock Update =====
export async function updateStock(payload: StockUpdatePayload): Promise<{ success: boolean }> {
  return fetchApi("/api/inventory/update-stock", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
