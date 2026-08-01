"use client";
import { useEffect, useRef, useState, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from "recharts";
import {
  Shield, Monitor, Cpu, Activity,
  AlertTriangle, CheckCircle2, LogOut, RefreshCw, Wifi
} from "lucide-react";
import {
  getDevices, getLatestMetric, getUnresolvedAlerts, getMe,
  tokenStore, Device, Metric, Alert
} from "@/lib/api";
import { useLiveMetrics } from "@/hooks/useLiveMetrics";

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

// ── Device row — receives live metric from parent so it always reflects WS data
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

// ── Live hook for the primary device shown on the dashboard chart ─────────────
function PrimaryDeviceChart({
  deviceUuid,
  initialHistory,
}: {
  deviceUuid: string;
  initialHistory: { t: string; cpu: number; ram: number }[];
}) {
  const [history, setHistory] = useState(initialHistory);
  const { latest: wsLatest, connected } = useLiveMetrics(deviceUuid);

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
            {connected ? "Live" : "Polling"}
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
          Waiting for first metric push...
        </div>
      )}
    </div>
  );
}

// ── Device metrics store: uuid → latest Metric ─────────────────────────────────
type MetricsMap = Record<string, Metric>;

// ── Main Dashboard ─────────────────────────────────────────────────────────────
export default function DashboardPage() {
  const router = useRouter();
  const [devices, setDevices] = useState<Device[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [user, setUser] = useState<{ email: string } | null>(null);
  const [metricsMap, setMetricsMap] = useState<MetricsMap>({});
  const [initialHistory, setInitialHistory] = useState<{ t: string; cpu: number; ram: number }[]>([]);
  const [primaryUuid, setPrimaryUuid] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const intervalRef = useRef<ReturnType<typeof setInterval>>();

  const load = useCallback(async () => {
    try {
      const [devs, me] = await Promise.all([getDevices(), getMe()]);
      setDevices(devs);
      setUser(me);

      // Collect unresolved alerts
      const allAlerts: Alert[] = [];
      await Promise.all(
        devs.slice(0, 10).map(async (d) => {
          try {
            const r = await getUnresolvedAlerts(d.device_uuid);
            allAlerts.push(...r.alerts);
          } catch {}
        })
      );
      setAlerts(allAlerts);

      // Fetch latest metric for every device — used in DeviceRow gauges
      const newMap: MetricsMap = {};
      await Promise.all(
        devs.map(async (d) => {
          try {
            newMap[d.device_uuid] = await getLatestMetric(d.device_uuid);
          } catch {}
        })
      );
      setMetricsMap(newMap);

      // Determine primary device (first online) for chart
      const primary = devs.find((d) => d.is_online);
      if (primary) {
        setPrimaryUuid((prev) => prev ?? primary.device_uuid);

        // Seed chart with last 10 REST data points only on first load
        if (initialHistory.length === 0) {
          const m = await getLatestMetric(primary.device_uuid);
          const now = new Date().toLocaleTimeString("en", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
          setInitialHistory([{ t: now, cpu: m.cpu_usage_percent ?? 0, ram: m.ram_usage_percent ?? 0 }]);
        }
      }
    } catch {
      router.push("/login");
    } finally {
      setLoading(false);
    }
  }, [initialHistory.length, router]);

  useEffect(() => {
    if (!tokenStore.getAccess()) { router.push("/login"); return; }
    load();
    // Poll every 10s as a safety net — WebSocket handles real-time updates
    intervalRef.current = setInterval(load, 10000);
    return () => clearInterval(intervalRef.current);
  }, []);

  const onlineCount = devices.filter((d) => d.is_online).length;
  const criticalCount = alerts.filter((a) => a.severity === "critical").length;

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin mx-auto mb-4" />
          <p className="text-slate-400">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen" style={{ background: "radial-gradient(ellipse at top left, #1e1b4b 0%, #030712 50%)" }}>
      {/* Navbar */}
      <nav className="border-b border-slate-800 px-6 py-4 flex items-center justify-between"
        style={{ background: "rgba(3,7,18,0.8)", backdropFilter: "blur(12px)", position: "sticky", top: 0, zIndex: 50 }}>
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center"
            style={{ background: "linear-gradient(135deg,#6366f1,#8b5cf6)" }}>
            <Shield className="w-4 h-4 text-white" />
          </div>
          <span className="font-bold text-white text-lg">InfraMind AI</span>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-slate-400 text-sm hidden md:block">{user?.email}</span>
          <button onClick={load} className="p-2 text-slate-400 hover:text-white transition-colors" title="Refresh">
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={() => { tokenStore.clear(); router.push("/login"); }}
            className="flex items-center gap-1 text-slate-400 hover:text-red-400 transition-colors text-sm">
            <LogOut className="w-4 h-4" /> Logout
          </button>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto p-6 space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="text-slate-400 text-sm mt-1">Real-time infrastructure overview</p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard icon={Monitor} label="Total Devices" value={devices.length} color="#6366f1" />
          <StatCard icon={CheckCircle2} label="Online" value={onlineCount} color="#22c55e"
            sublabel={`${devices.length - onlineCount} offline`} />
          <StatCard icon={AlertTriangle} label="Active Alerts" value={alerts.length} color="#f59e0b"
            sublabel={criticalCount > 0 ? `${criticalCount} critical` : "All clear"} />
          <StatCard icon={Activity} label="Metrics / min" value={onlineCount * 12} color="#8b5cf6"
            sublabel="5s interval per device" />
        </div>

        {/* Live CPU/RAM chart + Alerts */}
        <div className="grid lg:grid-cols-2 gap-6">
          {/* Chart — isolated component owns its own WS connection */}
          {primaryUuid ? (
            <PrimaryDeviceChart deviceUuid={primaryUuid} initialHistory={initialHistory} />
          ) : (
            <div className="glass p-5 h-[300px] flex items-center justify-center text-slate-500 text-sm">
              No online devices yet. Start the Windows agent.
            </div>
          )}

          {/* Alerts */}
          <div className="glass p-5">
            <h2 className="font-semibold text-white mb-4 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-400" /> Active Alerts
              {alerts.length > 0 && (
                <span className="ml-auto text-xs bg-amber-500/10 text-amber-400 px-2 py-0.5 rounded-full">{alerts.length}</span>
              )}
            </h2>
            <div className="space-y-2 max-h-[260px] overflow-y-auto">
              {alerts.length === 0 ? (
                <div className="flex items-center gap-2 text-green-400 text-sm">
                  <CheckCircle2 className="w-4 h-4" /> No active alerts — all systems nominal
                </div>
              ) : alerts.slice(0, 8).map((a) => (
                <div key={a.id} className={`flex items-start gap-3 p-3 rounded-lg border text-sm
                  ${a.severity === "critical" ? "border-red-500/30 bg-red-500/5" :
                    a.severity === "warning" ? "border-amber-500/30 bg-amber-500/5" : "border-slate-700 bg-slate-800/50"}`}>
                  <AlertTriangle className={`w-4 h-4 mt-0.5 flex-shrink-0
                    ${a.severity === "critical" ? "text-red-400" : "text-amber-400"}`} />
                  <div className="min-w-0">
                    <p className="font-medium text-white truncate">{a.title}</p>
                    <p className="text-slate-400 text-xs mt-0.5 truncate">{a.message}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Device list */}
        <div>
          <h2 className="font-semibold text-white mb-4 flex items-center gap-2">
            <Monitor className="w-4 h-4 text-indigo-400" /> Monitored Endpoints
            <span className="ml-auto text-xs text-slate-500">{onlineCount}/{devices.length} online</span>
          </h2>
          <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
            {devices.length === 0 ? (
              <div className="glass p-8 text-center text-slate-400 col-span-full">
                No devices registered yet. Start the Windows agent to see endpoints here.
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
