/**
 * Centralised API client for InfraMind AI backend.
 * All fetch calls go through these functions — token management is handled here.
 */

function getApiBase(): string {
  let url = process.env.NEXT_PUBLIC_API_URL || "https://inframindai.onrender.com/api/v1";
  url = url.trim().replace(/\/+$/, "");
  if (!url.endsWith("/api/v1")) {
    url = `${url}/api/v1`;
  }
  return url;
}

const API = getApiBase();

// ── Token storage (localStorage, client-side only) ────────────────────────────
export const tokenStore = {
  getAccess: () => (typeof window !== "undefined" ? localStorage.getItem("access_token") ?? "" : ""),
  getRefresh: () => (typeof window !== "undefined" ? localStorage.getItem("refresh_token") ?? "" : ""),
  set: (access: string, refresh: string) => {
    localStorage.setItem("access_token", access);
    localStorage.setItem("refresh_token", refresh);
  },
  clear: () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
  },
};

// ── Core fetch wrapper ────────────────────────────────────────────────────────
async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
  auth = true
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (auth) headers["Authorization"] = `Bearer ${tokenStore.getAccess()}`;

  const res = await fetch(`${API}${path}`, { ...options, headers });

  // Auto-refresh on 401
  if (res.status === 401 && auth) {
    const refreshed = await tryRefresh();
    if (refreshed) {
      headers["Authorization"] = `Bearer ${tokenStore.getAccess()}`;
      const retry = await fetch(`${API}${path}`, { ...options, headers });
      if (!retry.ok) throw new Error(await retry.text());
      return retry.json();
    }
    tokenStore.clear();
    window.location.href = "/login";
    throw new Error("Session expired");
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? res.statusText);
  }
  return res.json();
}

async function tryRefresh(): Promise<boolean> {
  try {
    const data = await fetch(`${API}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: tokenStore.getRefresh() }),
    }).then((r) => r.json());
    if (data.access_token) {
      tokenStore.set(data.access_token, data.refresh_token ?? tokenStore.getRefresh());
      return true;
    }
  } catch {}
  return false;
}

// ── Auth ──────────────────────────────────────────────────────────────────────
export async function login(email: string, password: string) {
  const data = await apiFetch<{ access_token: string; refresh_token: string }>(
    "/auth/login",
    { method: "POST", body: JSON.stringify({ email, password }) },
    false
  );
  tokenStore.set(data.access_token, data.refresh_token);
  return data;
}

export async function register(email: string, password: string, full_name: string) {
  return apiFetch("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password, full_name }),
  }, false);
}

export async function getMe() {
  return apiFetch<{ id: number; email: string; full_name: string; is_active: boolean; is_superuser: boolean }>("/auth/me");
}

// ── Admin Portal ──────────────────────────────────────────────────────────────
export interface AdminOverview {
  total_users: number;
  active_users: number;
  total_devices: number;
  online_devices: number;
  offline_devices: number;
  avg_cpu_percent: number;
  avg_ram_percent: number;
  total_alerts: number;
  unresolved_alerts: number;
}

export interface UserAdminView {
  id: number;
  email: string;
  full_name: string;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
  device_count: number;
}

export async function getAdminOverview() {
  return apiFetch<AdminOverview>("/admin/overview");
}

export async function getAdminUsers(q?: string) {
  const query = q ? `?q=${encodeURIComponent(q)}` : "";
  return apiFetch<UserAdminView[]>(`/admin/users${query}`);
}

export async function toggleDisableUser(userId: number) {
  return apiFetch<UserAdminView>(`/admin/users/${userId}/toggle-disable`, { method: "POST" });
}

export async function deleteUser(userId: number) {
  return apiFetch(`/admin/users/${userId}`, { method: "DELETE" });
}

export async function resetUserPassword(userId: number, newPassword: string) {
  return apiFetch<{ message: string }>(`/admin/users/${userId}/reset-password`, {
    method: "POST",
    body: JSON.stringify({ new_password: newPassword }),
  });
}

export async function assignDevice(uuid: string, userId: number) {
  return apiFetch<Device>(`/admin/devices/${uuid}/assign`, {
    method: "POST",
    body: JSON.stringify({ user_id: userId }),
  });
}

export async function exportAdminReport() {
  return apiFetch<any>("/admin/reports/export");
}

// ── Devices ───────────────────────────────────────────────────────────────────
export async function getDevices() {
  return apiFetch<Device[]>("/devices/");
}

export async function getDevice(uuid: string) {
  return apiFetch<Device>(`/devices/${uuid}`);
}

export async function renameDevice(uuid: string, display_name: string) {
  return apiFetch<Device>(`/devices/${uuid}`, {
    method: "PATCH",
    body: JSON.stringify({ display_name }),
  });
}

export async function deleteDevice(uuid: string) {
  return apiFetch(`/devices/${uuid}`, { method: "DELETE" });
}

export async function toggleDisableDevice(uuid: string) {
  return apiFetch<Device>(`/devices/${uuid}/toggle-disable`, { method: "POST" });
}

export function getDownloadAgentUrl(): string {
  return `${API}/download/agent`;
}

// ── Metrics ───────────────────────────────────────────────────────────────────
export async function getLatestMetric(uuid: string) {
  return apiFetch<Metric>(`/metrics/${uuid}/latest`);
}

export async function getMetricHistory(uuid: string, limit = 60) {
  return apiFetch<MetricHistoryResponse>(`/metrics/${uuid}/history?limit=${limit}`);
}

// ── Alerts ────────────────────────────────────────────────────────────────────
export async function getAlerts(uuid: string) {
  return apiFetch<AlertListResponse>(`/alerts/${uuid}`);
}

export async function getUnresolvedAlerts(uuid: string) {
  return apiFetch<AlertListResponse>(`/alerts/${uuid}/unresolved`);
}

export async function getUserUnresolvedAlerts() {
  return apiFetch<Alert[]>("/alerts/user/unresolved");
}

export async function resolveAlert(alertId: number) {
  return apiFetch(`/alerts/${alertId}/resolve`, { method: "POST" });
}

export async function resolveAllUserAlerts() {
  return apiFetch<{ status: string; resolved_count: number }>("/alerts/user/resolve-all", { method: "POST" });
}

export async function triggerTestAlert(deviceUuid?: string, alertType = "suspicious_process") {
  const query = new URLSearchParams();
  if (deviceUuid) query.append("device_uuid", deviceUuid);
  query.append("alert_type", alertType);
  return apiFetch<Alert>(`/alerts/test?${query.toString()}`, { method: "POST" });
}


// ── Types ─────────────────────────────────────────────────────────────────────
export interface Device {
  id: number;
  device_uuid: string;
  hostname: string;
  display_name?: string | null;
  os_name: string;
  os_version: string;
  architecture: string;
  agent_version: string;
  mac_address?: string | null;
  ip_address?: string | null;
  is_online: boolean;
  is_disabled?: boolean;
  last_seen_at: string | null;
  created_at: string;
}

export interface Metric {
  id: number;
  device_id: number;
  collected_at: string | null;
  created_at: string;
  cpu_usage_percent: number | null;
  ram_usage_percent: number | null;
  disk_usage_percent: number | null;
  network_bytes_sent: number | null;
  network_bytes_recv: number | null;
  upload_speed_bps: number | null;
  download_speed_bps: number | null;
  battery_percent: number | null;
  uptime_seconds: number | null;
  total_processes: number | null;
  suspicious_process_count: number | null;
}

export interface MetricHistoryResponse {
  device_id: number;
  total_stored: number;
  metrics: Metric[];
}

export interface Alert {
  id: number;
  device_id: number;
  metric_id: number | null;
  severity: "info" | "warning" | "critical";
  title: string;
  message: string;
  is_resolved: boolean;
  resolved_at: string | null;
  created_at: string;
}

export interface AlertListResponse {
  device_id: number;
  total: number;
  alerts: Alert[];
}
