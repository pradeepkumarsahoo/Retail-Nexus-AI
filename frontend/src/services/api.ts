// Author: Pradeep Sahoo — Retail Nexus AI
const BASE = (import.meta as any).env?.VITE_API_BASE || "/api/v1";

function getToken(): string | null {
  return localStorage.getItem("ct_token");
}

export function setToken(t: string | null) {
  if (t) localStorage.setItem("ct_token", t);
  else localStorage.removeItem("ct_token");
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init.headers as Record<string, string> | undefined),
  };
  const t = getToken();
  if (t) headers["Authorization"] = `Bearer ${t}`;
  const res = await fetch(`${BASE}${path}`, { ...init, headers });
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail ?? detail; } catch {}
    throw new Error(`${res.status}: ${detail}`);
  }
  if (res.status === 204) return undefined as unknown as T;
  return (await res.json()) as T;
}

export const api = {
  login: async (username: string, password: string) => {
    const body = new URLSearchParams({ username, password });
    const res = await fetch(`${BASE}/auth/token`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body,
    });
    if (!res.ok) throw new Error(`Login failed (${res.status})`);
    return res.json() as Promise<{ access_token: string; role: string; display_name: string }>;
  },
  health: () => request<any>("/health"),
  dashboard: () => request<any>("/dashboard/summary"),
  exceptions: (params: Record<string, string | number | undefined> = {}) => {
    const q = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => v !== undefined && q.append(k, String(v)));
    return request<any>(`/exceptions?${q.toString()}`);
  },
  exception: (id: string) => request<any>(`/exceptions/${id}`),
  detect: () => request<any>(`/exceptions/detect`, { method: "POST", body: "{}" }),
  investigate: (id: string) => request<any>(`/exceptions/${id}/investigate`, { method: "POST", body: "{}" }),
  recommendations: (params: Record<string, string | number | undefined> = {}) => {
    const q = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => v !== undefined && q.append(k, String(v)));
    return request<any>(`/recommendations?${q.toString()}`);
  },
  recommendation: (id: string) => request<any>(`/recommendations/${id}`),
  approve: (id: string, comment?: string) =>
    request<any>(`/recommendations/${id}/approve`, { method: "POST", body: JSON.stringify({ comment }) }),
  reject: (id: string, comment?: string) =>
    request<any>(`/recommendations/${id}/reject`, { method: "POST", body: JSON.stringify({ comment }) }),
  requestEvidence: (id: string, comment?: string) =>
    request<any>(`/recommendations/${id}/request-evidence`, { method: "POST", body: JSON.stringify({ comment }) }),
  suppliers: () => request<any>(`/suppliers`),
  products: () => request<any>(`/products`),
  stores: () => request<any>(`/stores`),
  demand: (product_id: string, store_id: string, horizon_days = 14) =>
    request<any>(`/analytics/demand?product_id=${product_id}&store_id=${store_id}&horizon_days=${horizon_days}`),
  stockoutRisk: (product_id: string, store_id: string, horizon_days = 14) =>
    request<any>(`/analytics/stockout-risk?product_id=${product_id}&store_id=${store_id}&horizon_days=${horizon_days}`),
  runs: (exception_id?: string) => request<any>(`/agents/runs${exception_id ? `?exception_id=${exception_id}` : ""}`),
  simulate: (body: any) =>
    request<any>(`/simulations/run`, { method: "POST", body: JSON.stringify(body) }),
};
