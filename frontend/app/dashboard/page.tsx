"use client";
import { useEffect, useRef, useState, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from "recharts";
import {
  Shield, Monitor, Cpu, Activity,
  AlertTriangle, CheckCircle2, LogOut, RefreshCw, Bell, X, Zap,
  Volume2, VolumeX, ShieldAlert, AlertCircle, Sparkles, Check,
  Download, Edit2, Trash2, Power, Search
} from "lucide-react";
import {
  getDevices, getLatestMetric, getMe,
  tokenStore, Device, Metric, Alert,
  getUserUnresolvedAlerts, resolveAlert, resolveAllUserAlerts, triggerTestAlert,
  renameDevice, deleteDevice, toggleDisableDevice, getDownloadAgentUrl
} from "@/lib/api";
import { useLiveMetrics } from "@/hooks/useLiveMetrics";

// ── Web Audio Synth for Alert Chimes ──────────────────────────────────────────
function playAlertChime(severity: "warning" | "critical") {
  if (typeof window === "undefined") return;
  try {
    const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
    if (!AudioCtx) return;
    const ctx = new AudioCtx();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.type = severity === "critical" ? "sawtooth" : "sine";
    osc.frequency.setValueAtTime(severity === "critical" ? 880 : 587.33, ctx.currentTime);
    if (severity === "critical") {
      osc.frequency.exponentialRampToValueAtTime(440, ctx.currentTime + 0.3);
    }
    gain.gain.setValueAtTime(0.15, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.35);

    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + 0.35);
  } catch {}
}

// ── Desktop Notification Helper ────────────────────────────────────────────────
function sendDesktopNotification(title: string, body: string) {
  if (typeof window !== "undefined" && "Notification" in window && Notification.permission === "granted") {
    try {
      new Notification(`[InfraMind AI] ${title}`, {
        body,
        icon: "/favicon.ico",
      });
    } catch {}
  }
}

// ── Stat card ─────────────────────────────────────────────────────────────────
function StatCard({ icon: Icon, label, value, unit, color, sublabel }: {
  icon: React.ElementType; label: string; value: string | number;
  unit?: string; color: string; sublabel?: string;
}) {
  return (
    <div className="glass p-5 flex items-start gap-4 hover:scale-[1.01] transition-transform">
      <div className="p-3 rounded-xl" style={{ background: `${color}20` }}>
        <Icon className="w-6 h-6" style={{ color }} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-slate-400 text-sm">{label}</p>
        <p className="text-2xl font-bold text-white mt-0.5">
          {value}<span className="text-sm font-normal text-slate-400 ml-1">{unit}</span>
        </p>
        {sublabel && <p className="text-xs text-slate-500 mt-0.5 truncate">{sublabel}</p>}
      </div>
    </div>
  );
}

// ── Mini gauge bar ─────────────────────────────────────────────────────────────
function GaugeBar({ value, color }: { value: number; color: string }) {
  const pct = Math.min(100, Math.max(0, value));
  return (
    <div className="h-1.5 rounded-full bg-slate-700 overflow-hidden">
      <div className="h-full rounded-full transition-all duration-500"
        style={{ width: `${pct}%`, background: color }} />
    </div>
  );
}

// ── Device row ─────────────────────────────────────────────────────────────────
function DeviceRow({ device, liveMetric }: { device: Device; liveMetric: Metric | null }) {
  const cpu = liveMetric?.cpu_usage_percent ?? 0;
  const ram = liveMetric?.ram_usage_percent ?? 0;

  return (
    <Link href={`/devices/${device.device_uuid}`}
      className="glass p-4 flex items-center gap-4 hover:border-indigo-500/40 transition-all group">
      <div className="relative">
        <Monitor className="w-8 h-8 text-slate-400" />
        <span className={`absolute -top-1 -right-1 w-3 h-3 rounded-full border-2 border-gray-950
          ${device.is_online ? "bg-green-400 status-dot" : "bg-slate-600"}`} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="font-semibold text-white group-hover:text-indigo-300 transition-colors truncate">{device.hostname}</p>
        <p className="text-xs text-slate-500">{device.os_name} · {device.architecture}</p>
        <div className="flex gap-3 mt-2">
          <div className="flex-1">
            <div className="flex justify-between text-xs text-slate-400 mb-1">
              <span>CPU</span><span>{cpu.toFixed(1)}%</span>
            </div>
            <GaugeBar value={cpu} color={cpu > 85 ? "#ef4444" : cpu > 60 ? "#f59e0b" : "#6366f1"} />
          </div>
          <div className="flex-1">
            <div className="flex justify-between text-xs text-slate-400 mb-1">
              <span>RAM</span><span>{ram.toFixed(1)}%</span>
            </div>
            <GaugeBar value={ram} color={ram > 80 ? "#ef4444" : ram > 60 ? "#f59e0b" : "#22c55e"} />
          </div>
        </div>
      </div>
      <div className="text-right">
        <span className={`text-xs px-2 py-1 rounded-full font-medium
          ${device.is_online ? "bg-green-500/10 text-green-400" : "bg-slate-700 text-slate-400"}`}>
          {device.is_online ? "Online" : "Offline"}
        </span>
      </div>
    </Link>
  );
}

// ── Primary Device Chart & Live Alert Listener ─────────────────────────────────
function PrimaryDeviceChart({
  deviceUuid,
  initialHistory,
  onLiveAlert,
}: {
  deviceUuid: string;
  initialHistory: { t: string; cpu: number; ram: number }[];
  onLiveAlert: (alertData: any) => void;
}) {
  const [history, setHistory] = useState(initialHistory);

  const handleAlert = useCallback((alertData: any) => {
    onLiveAlert(alertData);
  }, [onLiveAlert]);

  const { latest: wsLatest, connected } = useLiveMetrics(deviceUuid, handleAlert);

  useEffect(() => {
    if (!wsLatest || wsLatest.type !== "metric") return;
    const now = new Date().toLocaleTimeString("en", {
      hour: "2-digit", minute: "2-digit", second: "2-digit"
    });
    setHistory((prev) => {
      const next = [...prev, {
        t: now,
        cpu: wsLatest.cpu_usage_percent ?? 0,
        ram: wsLatest.ram_usage_percent ?? 0,
      }];
      return next.slice(-30);
    });
  }, [wsLatest]);

  return (
    <div className="glass p-5">
      <h2 className="font-semibold text-white mb-4 flex items-center gap-2">
        <Cpu className="w-4 h-4 text-indigo-400" /> Live Metrics Trend
        <span className="ml-auto flex items-center gap-1.5 text-xs">
          <span className={`w-2 h-2 rounded-full ${connected ? "bg-green-400 status-dot" : "bg-slate-600"}`} />
          <span className={connected ? "text-green-400" : "text-slate-500"}>
            {connected ? "Live WebSocket Stream" : "Polling Mode"}
          </span>
        </span>
      </h2>
      {history.length > 1 ? (
        <ResponsiveContainer width="100%" height={220}>
          <AreaChart data={history}>
            <defs>
              <linearGradient id="cpuGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="ramGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
            <XAxis dataKey="t" tick={{ fill: "#64748b", fontSize: 11 }} />
            <YAxis domain={[0, 100]} tick={{ fill: "#64748b", fontSize: 11 }} unit="%" />
            <Tooltip
              contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: "8px" }}
              labelStyle={{ color: "#94a3b8" }}
            />
            <Area type="monotone" dataKey="cpu" name="CPU" stroke="#6366f1"
              fill="url(#cpuGrad)" strokeWidth={2} dot={false} />
            <Area type="monotone" dataKey="ram" name="RAM" stroke="#22c55e"
              fill="url(#ramGrad)" strokeWidth={2} dot={false} />
          </AreaChart>
        </ResponsiveContainer>
      ) : (
        <div className="h-[220px] flex items-center justify-center text-slate-500 text-sm">
          Waiting for telemetry push...
        </div>
      )}
    </div>
  );
}

// ── Device metrics store: uuid → latest Metric ─────────────────────────────────
type MetricsMap = Record<string, Metric>;

export default function DashboardPage() {
  const router = useRouter();
  const [devices, setDevices] = useState<Device[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [user, setUser] = useState<{ email: string; full_name?: string; is_superuser?: boolean } | null>(null);
  const [metricsMap, setMetricsMap] = useState<MetricsMap>({});
  const [initialHistory, setInitialHistory] = useState<{ t: string; cpu: number; ram: number }[]>([]);
  const [primaryUuid, setPrimaryUuid] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Alert Center & Toast State
  const [alertDrawerOpen, setAlertDrawerOpen] = useState(false);
  const [toastAlerts, setToastAlerts] = useState<(Alert & { toastId: string })[]>([]);
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Request browser desktop notification permissions on load
  useEffect(() => {
    if (typeof window !== "undefined" && "Notification" in window) {
      if (Notification.permission === "default") {
        Notification.requestPermission().catch(() => {});
      }
    }
  }, []);

  const load = useCallback(async () => {
    try {
      const me = await getMe();
      setUser(me);

      const [devs, userAlerts] = await Promise.all([
        getDevices().catch(() => []),
        getUserUnresolvedAlerts().catch(() => []),
      ]);

      setDevices(devs);
      setAlerts(userAlerts);

      if (devs.length > 0) {
        // Fetch latest metric for every device
        const newMap: MetricsMap = {};
        await Promise.all(
          devs.map(async (d) => {
            try {
              newMap[d.device_uuid] = await getLatestMetric(d.device_uuid);
            } catch {}
          })
        );
        setMetricsMap(newMap);

        // Determine primary device for chart
        const primary = devs.find((d) => d.is_online) || devs[0];
        if (primary) {
          setPrimaryUuid((prev) => prev ?? primary.device_uuid);

          if (initialHistory.length === 0) {
            try {
              const m = await getLatestMetric(primary.device_uuid);
              const now = new Date().toLocaleTimeString("en", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
              setInitialHistory([{ t: now, cpu: m.cpu_usage_percent ?? 0, ram: m.ram_usage_percent ?? 0 }]);
            } catch {}
          }
        }
      }
    } catch (err: any) {
      console.error("Dashboard load error:", err);
      if (err?.message === "Session expired" || err?.message?.includes("401") || err?.message?.includes("Could not validate credentials")) {
        tokenStore.clear();
        window.location.href = "/login";
      }
    } finally {
      setLoading(false);
    }
  }, [initialHistory.length]);

  // Handle incoming live alert push (WebSocket / Test Alert)
  const handleLiveAlertReceived = useCallback((alertData: any) => {
    const newAlert: Alert = {
      id: alertData.id ?? Date.now(),
      device_id: 0,
      metric_id: null,
      severity: alertData.severity ?? "warning",
      title: alertData.title ?? "System Alert",
      message: alertData.message ?? "Anomalous activity detected.",
      is_resolved: false,
      resolved_at: null,
      created_at: alertData.created_at ?? new Date().toISOString(),
    };

    setAlerts((prev) => [newAlert, ...prev.filter((a) => a.id !== newAlert.id)]);

    // Trigger toast notification
    const toastId = `${newAlert.id}-${Date.now()}`;
    setToastAlerts((prev) => [{ ...newAlert, toastId }, ...prev.slice(0, 4)]);

    // Play sound chime if enabled
    if (soundEnabled) {
      playAlertChime(newAlert.severity as "warning" | "critical");
    }

    // Trigger OS desktop notification
    sendDesktopNotification(newAlert.title, newAlert.message);

    // Auto-dismiss toast after 7s
    setTimeout(() => {
      setToastAlerts((prev) => prev.filter((t) => t.toastId !== toastId));
    }, 7000);
  }, [soundEnabled]);

  useEffect(() => {
    if (!tokenStore.getAccess()) { window.location.href = "/login"; return; }
    load();
    intervalRef.current = setInterval(load, 10000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [load]);

  const handleResolveAlert = async (alertId: number) => {
    try {
      await resolveAlert(alertId);
      setAlerts((prev) => prev.filter((a) => a.id !== alertId));
      setToastAlerts((prev) => prev.filter((t) => t.id !== alertId));
    } catch (e: any) {
      console.error("Resolve failed:", e);
    }
  };

  const handleResolveAll = async () => {
    setActionLoading(true);
    try {
      await resolveAllUserAlerts();
      setAlerts([]);
      setToastAlerts([]);
    } catch (e: any) {
      console.error("Resolve all failed:", e);
    } finally {
      setActionLoading(false);
    }
  };

  const handleTriggerTest = async (alertType: string) => {
    setActionLoading(true);
    try {
      const generated = await triggerTestAlert(primaryUuid ?? undefined, alertType);
      handleLiveAlertReceived(generated);
    } catch (e: any) {
      console.error("Trigger test alert failed:", e);
    } finally {
      setActionLoading(false);
    }
  };

  const onlineCount = devices.filter((d) => d.is_online).length;
  const criticalCount = alerts.filter((a) => a.severity === "critical").length;

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-950">
        <div className="text-center">
          <div className="w-12 h-12 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin mx-auto mb-4" />
          <p className="text-slate-400">Loading InfraMind Admin Dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen relative" style={{ background: "radial-gradient(ellipse at top left, #1e1b4b 0%, #030712 50%)" }}>
      
      {/* ── REAL-TIME FLOATING TOAST ALERTS ─────────────────────────────────── */}
      <div className="fixed top-20 right-6 z-50 flex flex-col gap-3 max-w-md w-full pointer-events-none">
        {toastAlerts.map((toast) => (
          <div
            key={toast.toastId}
            className={`pointer-events-auto p-4 rounded-xl shadow-2xl border backdrop-blur-xl flex items-start gap-3 animate-slide-in transition-all
              ${toast.severity === "critical"
                ? "bg-red-950/90 border-red-500/60 text-red-200 shadow-red-900/40"
                : "bg-amber-950/90 border-amber-500/60 text-amber-200 shadow-amber-900/40"}`}
          >
            <ShieldAlert className={`w-6 h-6 flex-shrink-0 mt-0.5 ${toast.severity === "critical" ? "text-red-400 animate-pulse" : "text-amber-400"}`} />
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-2">
                <span className={`text-xs font-bold uppercase tracking-wider px-2 py-0.5 rounded-md
                  ${toast.severity === "critical" ? "bg-red-500/20 text-red-300" : "bg-amber-500/20 text-amber-300"}`}>
                  {toast.severity} Alert
                </span>
                <span className="text-xs text-slate-400">Just Now</span>
              </div>
              <p className="font-semibold text-white mt-1 text-sm">{toast.title}</p>
              <p className="text-xs text-slate-300 mt-0.5 line-clamp-2">{toast.message}</p>
              
              <div className="flex items-center gap-2 mt-3">
                <button
                  onClick={() => handleResolveAlert(toast.id)}
                  className="px-2.5 py-1 text-xs font-medium bg-white/10 hover:bg-white/20 text-white rounded-lg transition-colors flex items-center gap-1"
                >
                  <Check className="w-3 h-3" /> Resolve
                </button>
                {primaryUuid && (
                  <Link
                    href={`/devices/${primaryUuid}`}
                    className="px-2.5 py-1 text-xs font-medium bg-indigo-600/60 hover:bg-indigo-600 text-white rounded-lg transition-colors"
                  >
                    Diagnose Endpoint →
                  </Link>
                )}
              </div>
            </div>
            <button
              onClick={() => setToastAlerts((prev) => prev.filter((t) => t.toastId !== toast.toastId))}
              className="text-slate-400 hover:text-white transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        ))}
      </div>

      {/* ── TOP NAVBAR ───────────────────────────────────────────────────────── */}
      <nav className="border-b border-slate-800 px-6 py-4 flex items-center justify-between"
        style={{ background: "rgba(3,7,18,0.85)", backdropFilter: "blur(16px)", position: "sticky", top: 0, zIndex: 40 }}>
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-500/20"
            style={{ background: "linear-gradient(135deg,#6366f1,#8b5cf6)" }}>
            <Shield className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-white text-lg tracking-tight">InfraMind AI</span>
              <span className="text-[10px] font-bold uppercase tracking-wider bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 px-2 py-0.5 rounded-full">
                Admin Console
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Audio Chime Toggle */}
          <button
            onClick={() => setSoundEnabled(!soundEnabled)}
            className={`p-2 rounded-lg border transition-colors ${soundEnabled ? "border-slate-700 bg-slate-800 text-indigo-400" : "border-slate-800 bg-slate-900 text-slate-500"}`}
            title={soundEnabled ? "Alert Chime Enabled" : "Alert Chime Muted"}
          >
            {soundEnabled ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
          </button>

          {/* Alert Bell Button */}
          <button
            onClick={() => setAlertDrawerOpen(!alertDrawerOpen)}
            className="relative p-2 text-slate-300 hover:text-white rounded-lg border border-slate-700 bg-slate-800/80 hover:bg-slate-700 transition-colors"
            title="Open Alert Center"
          >
            <Bell className="w-4 h-4" />
            {alerts.length > 0 && (
              <span className="absolute -top-1.5 -right-1.5 w-5 h-5 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center border-2 border-slate-950 animate-pulse">
                {alerts.length}
              </span>
            )}
          </button>

          <button onClick={load} className="p-2 text-slate-400 hover:text-white transition-colors" title="Refresh Dashboard">
            <RefreshCw className="w-4 h-4" />
          </button>

          <div className="h-4 w-px bg-slate-800 hidden md:block" />
          <span className="text-slate-400 text-xs hidden md:block">{user?.email}</span>

          {user?.is_superuser && (
            <Link
              href="/admin"
              className="flex items-center gap-1.5 text-indigo-400 hover:text-indigo-300 transition-colors text-xs bg-indigo-500/10 border border-indigo-500/30 px-3 py-1.5 rounded-lg font-semibold"
            >
              <Shield className="w-3.5 h-3.5" /> Admin Portal
            </Link>
          )}

          <button
            onClick={() => { tokenStore.clear(); router.push("/login"); }}
            className="flex items-center gap-1.5 text-slate-400 hover:text-red-400 transition-colors text-xs bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-lg">
            <LogOut className="w-3.5 h-3.5" /> Logout
          </button>
        </div>
      </nav>

      {/* ── ALERT CENTER DRAWER ──────────────────────────────────────────────── */}
      {alertDrawerOpen && (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-sm animate-fade-in">
          <div className="w-full max-w-md bg-slate-950 border-l border-slate-800 h-full p-6 flex flex-col shadow-2xl">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-amber-400" />
                <h2 className="font-bold text-white text-lg">Alert Center</h2>
                <span className="bg-amber-500/20 text-amber-300 text-xs font-semibold px-2 py-0.5 rounded-full">
                  {alerts.length} Active
                </span>
              </div>
              <button
                onClick={() => setAlertDrawerOpen(false)}
                className="text-slate-400 hover:text-white p-1"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Test Alert Simulator Panel */}
            <div className="my-4 p-4 rounded-xl border border-indigo-500/30 bg-indigo-950/20">
              <p className="text-xs font-semibold text-indigo-300 flex items-center gap-1.5 mb-2">
                <Zap className="w-3.5 h-3.5 text-indigo-400" /> Test Security Alert Delivery
              </p>
              <div className="grid grid-cols-2 gap-2">
                <button
                  disabled={actionLoading}
                  onClick={() => handleTriggerTest("suspicious_process")}
                  className="px-2.5 py-1.5 bg-slate-800 hover:bg-indigo-600 text-xs text-white rounded-lg transition-colors border border-slate-700 text-left truncate"
                >
                  ⚠️ Suspicious Exe
                </button>
                <button
                  disabled={actionLoading}
                  onClick={() => handleTriggerTest("high_cpu")}
                  className="px-2.5 py-1.5 bg-slate-800 hover:bg-indigo-600 text-xs text-white rounded-lg transition-colors border border-slate-700 text-left truncate"
                >
                  🔥 High CPU Spike
                </button>
                <button
                  disabled={actionLoading}
                  onClick={() => handleTriggerTest("high_memory")}
                  className="px-2.5 py-1.5 bg-slate-800 hover:bg-indigo-600 text-xs text-white rounded-lg transition-colors border border-slate-700 text-left truncate"
                >
                  💾 High RAM Usage
                </button>
                <button
                  disabled={actionLoading}
                  onClick={() => handleTriggerTest("ransomware_heuristic")}
                  className="px-2.5 py-1.5 bg-slate-800 hover:bg-red-600 text-xs text-white rounded-lg transition-colors border border-slate-700 text-left truncate"
                >
                  🚨 Ransomware Alert
                </button>
              </div>
            </div>

            {/* Actions */}
            {alerts.length > 0 && (
              <div className="flex justify-between items-center mb-3">
                <span className="text-xs text-slate-400">Unresolved Endpoint Alerts</span>
                <button
                  onClick={handleResolveAll}
                  disabled={actionLoading}
                  className="text-xs font-medium text-indigo-400 hover:text-indigo-300 transition-colors"
                >
                  Resolve All ({alerts.length})
                </button>
              </div>
            )}

            {/* Alert List */}
            <div className="flex-1 overflow-y-auto space-y-3 pr-1">
              {alerts.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-center p-6 text-slate-500">
                  <CheckCircle2 className="w-10 h-10 text-green-500 mb-2" />
                  <p className="text-sm font-semibold text-slate-300">All Systems Nominal</p>
                  <p className="text-xs text-slate-500 mt-1">No unresolved security or threshold alerts across monitored endpoints.</p>
                </div>
              ) : (
                alerts.map((a) => (
                  <div
                    key={a.id}
                    className={`p-4 rounded-xl border flex items-start gap-3 transition-all
                      ${a.severity === "critical" ? "bg-red-950/40 border-red-500/40" : "bg-slate-900 border-slate-800"}`}
                  >
                    <AlertTriangle className={`w-5 h-5 flex-shrink-0 mt-0.5 ${a.severity === "critical" ? "text-red-400" : "text-amber-400"}`} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded-full
                          ${a.severity === "critical" ? "bg-red-500/20 text-red-400" : "bg-amber-500/20 text-amber-400"}`}>
                          {a.severity}
                        </span>
                        <span className="text-[10px] text-slate-500">
                          {a.created_at ? new Date(a.created_at).toLocaleTimeString() : ""}
                        </span>
                      </div>
                      <p className="font-semibold text-white text-sm mt-1.5 leading-snug">{a.title}</p>
                      <p className="text-xs text-slate-400 mt-1 leading-relaxed">{a.message}</p>

                      <div className="mt-3 flex items-center justify-end gap-2">
                        <button
                          onClick={() => handleResolveAlert(a.id)}
                          className="px-2.5 py-1 text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg transition-colors border border-slate-700"
                        >
                          Mark Resolved
                        </button>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── MAIN CONTENT ────────────────────────────────────────────────────── */}
      <div className="max-w-7xl mx-auto p-6 space-y-6">
        
        {/* Banner */}
        <div className="glass p-6 border-indigo-500/30 bg-gradient-to-r from-indigo-950/40 via-purple-950/20 to-slate-950 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-indigo-400" />
              <h1 className="text-2xl font-bold text-white">System Admin & Telemetry Dashboard</h1>
            </div>
            <p className="text-slate-400 text-sm mt-1">
              Real-time endpoint telemetry, threshold alert rules, and AI incident analysis.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <a
              href={getDownloadAgentUrl()}
              download="InfraMindAgentSetup.exe"
              className="px-4 py-2.5 text-xs font-bold bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white rounded-xl shadow-lg shadow-emerald-600/30 transition-all flex items-center gap-2"
            >
              <Download className="w-4 h-4" /> Download Windows Agent
            </a>
            <button
              onClick={() => handleTriggerTest("suspicious_process")}
              className="px-3.5 py-2.5 text-xs font-semibold bg-amber-500/20 border border-amber-500/40 text-amber-300 hover:bg-amber-500/30 rounded-xl transition-all flex items-center gap-1.5"
            >
              <AlertTriangle className="w-3.5 h-3.5" /> Test Alert
            </button>
            <button
              onClick={() => setAlertDrawerOpen(true)}
              className="px-3.5 py-2.5 text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl shadow-lg shadow-indigo-600/30 transition-all flex items-center gap-1.5"
            >
              <Bell className="w-3.5 h-3.5" /> Alert Center ({alerts.length})
            </button>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard icon={Monitor} label="Total Endpoints" value={devices.length} color="#6366f1" />
          <StatCard icon={CheckCircle2} label="Online Status" value={onlineCount} color="#22c55e"
            sublabel={`${devices.length - onlineCount} offline`} />
          <StatCard icon={AlertTriangle} label="Active Alerts" value={alerts.length} color="#f59e0b"
            sublabel={criticalCount > 0 ? `${criticalCount} critical alerts` : "All clear"} />
          <StatCard icon={Activity} label="Telemetry Rate" value={onlineCount * 12} color="#8b5cf6"
            sublabel="5s push interval" />
        </div>

        {/* Live CPU/RAM chart + Active Alerts Summary */}
        <div className="grid lg:grid-cols-2 gap-6">
          {/* Chart */}
          {primaryUuid ? (
            <PrimaryDeviceChart
              deviceUuid={primaryUuid}
              initialHistory={initialHistory}
              onLiveAlert={handleLiveAlertReceived}
            />
          ) : (
            <div className="glass p-5 h-[300px] flex items-center justify-center text-slate-500 text-sm">
              No online devices connected. Launch the Windows agent to stream telemetry.
            </div>
          )}

          {/* Active Alerts Panel */}
          <div className="glass p-5 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-semibold text-white flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-amber-400" /> Active System Alerts
                  {alerts.length > 0 && (
                    <span className="text-xs bg-amber-500/10 text-amber-400 px-2 py-0.5 rounded-full">{alerts.length}</span>
                  )}
                </h2>
                {alerts.length > 0 && (
                  <button
                    onClick={handleResolveAll}
                    className="text-xs text-indigo-400 hover:underline"
                  >
                    Resolve All
                  </button>
                )}
              </div>
              
              <div className="space-y-2.5 max-h-[220px] overflow-y-auto pr-1">
                {alerts.length === 0 ? (
                  <div className="flex items-center gap-2 text-green-400 text-sm py-4">
                    <CheckCircle2 className="w-4 h-4" /> No active alerts — all security thresholds nominal
                  </div>
                ) : alerts.slice(0, 5).map((a) => (
                  <div key={a.id} className={`flex items-start justify-between gap-3 p-3 rounded-xl border text-sm
                    ${a.severity === "critical" ? "border-red-500/40 bg-red-500/10" :
                      a.severity === "warning" ? "border-amber-500/40 bg-amber-500/10" : "border-slate-700 bg-slate-800/50"}`}>
                    <div className="flex items-start gap-3 min-w-0">
                      <AlertTriangle className={`w-4 h-4 mt-0.5 flex-shrink-0
                        ${a.severity === "critical" ? "text-red-400" : "text-amber-400"}`} />
                      <div className="min-w-0">
                        <p className="font-medium text-white truncate">{a.title}</p>
                        <p className="text-slate-400 text-xs mt-0.5 line-clamp-1">{a.message}</p>
                      </div>
                    </div>
                    <button
                      onClick={() => handleResolveAlert(a.id)}
                      className="text-xs text-slate-400 hover:text-white bg-slate-800 px-2 py-1 rounded-md flex-shrink-0"
                    >
                      Resolve
                    </button>
                  </div>
                ))}
              </div>
            </div>

            <div className="mt-4 pt-3 border-t border-slate-800 flex justify-between items-center text-xs text-slate-400">
              <span>Threshold Rules: CPU &gt; 75% | RAM &gt; 75% | Suspicious &gt; 0</span>
              <button
                onClick={() => setAlertDrawerOpen(true)}
                className="text-indigo-400 hover:text-indigo-300 font-medium"
              >
                Alert Settings & Simulator →
              </button>
            </div>
          </div>
        </div>

        {/* Monitored Endpoints list */}
        <div>
          <h2 className="font-semibold text-white mb-4 flex items-center gap-2">
            <Monitor className="w-4 h-4 text-indigo-400" /> Monitored Endpoints
            <span className="ml-auto text-xs text-slate-500">{onlineCount}/{devices.length} online</span>
          </h2>
          <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
            {devices.length === 0 ? (
              <div className="glass p-8 text-center text-slate-400 col-span-full">
                No devices registered yet. Start the Windows agent to register endpoints automatically.
              </div>
            ) : devices.map((d) => (
              <DeviceRow key={d.id} device={d} liveMetric={metricsMap[d.device_uuid] ?? null} />
            ))}
          </div>
        </div>

      </div>
    </div>
  );
}

