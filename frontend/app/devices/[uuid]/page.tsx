"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar, Legend
} from "recharts";
import {
  Shield, ArrowLeft, Monitor, Cpu, HardDrive, Activity,
  AlertTriangle, CheckCircle2, Wifi, Battery, Clock, RefreshCw
} from "lucide-react";
import {
  getDevice, getLatestMetric, getMetricHistory, getAlerts, resolveAlert,
  tokenStore, Device, Metric, Alert
} from "@/lib/api";
import { useLiveMetrics, LiveMetric } from "@/hooks/useLiveMetrics";

// ── Metric card ───────────────────────────────────────────────────────────────
function MetricCard({ label, value, unit, icon: Icon, color, subtitle }: {
  label: string; value: string | number | null; unit?: string;
  icon: React.ElementType; color: string; subtitle?: string;
}) {
  const pct = typeof value === "number" ? Math.min(100, value) : null;
  return (
    <div className="glass p-5">
      <div className="flex items-center gap-2 mb-3">
        <Icon className="w-4 h-4" style={{ color }} />
        <span className="text-slate-400 text-sm">{label}</span>
      </div>
      <p className="text-3xl font-bold text-white">
        {value !== null ? value : "—"}
        <span className="text-sm font-normal text-slate-400 ml-1">{unit}</span>
      </p>
      {pct !== null && (
        <div className="mt-3 h-1.5 rounded-full bg-slate-700 overflow-hidden">
          <div className="h-full rounded-full transition-all duration-700"
            style={{ width: `${pct}%`, background: color }} />
        </div>
      )}
      {subtitle && <p className="text-xs text-slate-500 mt-2">{subtitle}</p>}
    </div>
  );
}

// ── Format helpers ────────────────────────────────────────────────────────────
const fmtBytes = (b: number | null) => !b ? "—" : b > 1e9 ? `${(b / 1e9).toFixed(1)} GB` : `${(b / 1e6).toFixed(1)} MB`;
const fmtSpeed = (bps: number | null) => !bps ? "—" : bps > 1e6 ? `${(bps / 1e6).toFixed(2)} MB/s` : `${(bps / 1024).toFixed(1)} KB/s`;
const fmtUptime = (s: number | null) => { if (!s) return "—"; const h = Math.floor(s / 3600); const m = Math.floor((s % 3600) / 60); return `${h}h ${m}m`; };
const fmtTime = (iso: string | null) => iso ? new Date(iso).toLocaleTimeString("en", { hour: "2-digit", minute: "2-digit", second: "2-digit" }) : "";

export default function DeviceDetailPage() {
  const { uuid } = useParams<{ uuid: string }>();
  const router = useRouter();
  const [device, setDevice] = useState<Device | null>(null);
  const [latest, setLatest] = useState<Metric | null>(null);
  const [history, setHistory] = useState<{ t: string; cpu: number; ram: number; disk: number }[]>([]);
  const [netHistory, setNetHistory] = useState<{ t: string; up: number; down: number }[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);

  // WebSocket live updates
  const { latest: wsLatest, connected } = useLiveMetrics(uuid);

  // Apply WS updates to the displayed metric and chart
  useEffect(() => {
    if (!wsLatest || wsLatest.type !== "metric") return;

    // Update all metric cards — works even before REST data arrives (prev may be null)
    setLatest((prev) => ({
      ...(prev ?? {} as Metric),
      cpu_usage_percent: wsLatest.cpu_usage_percent ?? prev?.cpu_usage_percent ?? null,
      ram_usage_percent: wsLatest.ram_usage_percent ?? prev?.ram_usage_percent ?? null,
      disk_usage_percent: wsLatest.disk_usage_percent ?? prev?.disk_usage_percent ?? null,
      network_bytes_sent: wsLatest.network_bytes_sent ?? prev?.network_bytes_sent ?? null,
      network_bytes_recv: wsLatest.network_bytes_recv ?? prev?.network_bytes_recv ?? null,
      upload_speed_bps: wsLatest.upload_speed_bps ?? prev?.upload_speed_bps ?? null,
      download_speed_bps: wsLatest.download_speed_bps ?? prev?.download_speed_bps ?? null,
      battery_percent: wsLatest.battery_percent ?? prev?.battery_percent ?? null,
      total_processes: wsLatest.total_processes ?? prev?.total_processes ?? null,
      uptime_seconds: wsLatest.uptime_seconds ?? prev?.uptime_seconds ?? null,
    } as Metric));

    const ts = fmtTime(wsLatest.collected_at ?? null);

    // Append to CPU/RAM/Disk chart history
    setHistory((prev) => {
      const next = [...prev, {
        t: ts,
        cpu: wsLatest.cpu_usage_percent ?? 0,
        ram: wsLatest.ram_usage_percent ?? 0,
        disk: wsLatest.disk_usage_percent ?? 0,
      }];
      return next.slice(-30);
    });

    // Append to Network Speed chart history
    setNetHistory((prev) => {
      const upKbps = (wsLatest.upload_speed_bps ?? 0) / 1024;
      const downKbps = (wsLatest.download_speed_bps ?? 0) / 1024;
      const next = [...prev, { t: ts, up: parseFloat(upKbps.toFixed(2)), down: parseFloat(downKbps.toFixed(2)) }];
      return next.slice(-30);
    });
  }, [wsLatest]);


  async function loadData() {
    if (!tokenStore.getAccess()) { router.push("/login"); return; }
    try {
      const [dev, metric, hist, alertData] = await Promise.all([
        getDevice(uuid),
        getLatestMetric(uuid),
        getMetricHistory(uuid, 30),
        getAlerts(uuid),
      ]);
      setDevice(dev);
      setLatest(metric);
      setAlerts(alertData.alerts);
      const reversed = hist.metrics.reverse();
      setHistory(reversed.map((m) => ({
        t: fmtTime(m.collected_at),
        cpu: m.cpu_usage_percent ?? 0,
        ram: m.ram_usage_percent ?? 0,
        disk: m.disk_usage_percent ?? 0,
      })));
      // Seed network speed chart from history
      setNetHistory(reversed.map((m) => ({
        t: fmtTime(m.collected_at),
        up: parseFloat(((m.upload_speed_bps ?? 0) / 1024).toFixed(2)),
        down: parseFloat(((m.download_speed_bps ?? 0) / 1024).toFixed(2)),
      })));
    } catch {
      router.push("/login");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadData(); }, [uuid]);

  async function handleResolve(alertId: number) {
    await resolveAlert(alertId);
    setAlerts((prev) => prev.map((a) => a.id === alertId ? { ...a, is_resolved: true } : a));
  }

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="w-10 h-10 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
    </div>
  );
  if (!device) return null;

  const unresolved = alerts.filter((a) => !a.is_resolved);

  return (
    <div className="min-h-screen" style={{ background: "radial-gradient(ellipse at top left, #1e1b4b 0%, #030712 50%)" }}>
      {/* Nav */}
      <nav className="border-b border-slate-800 px-6 py-4 flex items-center gap-4 sticky top-0 z-50"
        style={{ background: "rgba(3,7,18,0.9)", backdropFilter: "blur(12px)" }}>
        <Link href="/dashboard" className="text-slate-400 hover:text-white transition-colors">
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div className="flex items-center gap-2">
          <Shield className="w-5 h-5 text-indigo-400" />
          <span className="text-slate-400">InfraMind AI</span>
          <span className="text-slate-600">/</span>
          <span className="text-white font-semibold">{device.hostname}</span>
        </div>
        <div className="ml-auto flex items-center gap-3">
          {/* WS indicator */}
          <div className="flex items-center gap-1.5 text-xs">
            <span className={`w-2 h-2 rounded-full ${connected ? "bg-green-400 status-dot" : "bg-slate-600"}`} />
            <span className={connected ? "text-green-400" : "text-slate-500"}>
              {connected ? "Live" : "Reconnecting..."}
            </span>
          </div>
          <button onClick={loadData} className="p-2 text-slate-400 hover:text-white transition-colors">
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto p-6 space-y-6">
        {/* Device info banner */}
        <div className="glass p-5 flex flex-wrap items-center gap-6">
          <div className="relative">
            <Monitor className="w-12 h-12 text-indigo-400" />
            <span className={`absolute -top-1 -right-1 w-3.5 h-3.5 rounded-full border-2 border-gray-950 ${device.is_online ? "bg-green-400 status-dot" : "bg-slate-600"}`} />
          </div>
          <div className="flex-1">
            <h1 className="text-2xl font-bold text-white">{device.hostname}</h1>
            <p className="text-slate-400 text-sm">{device.os_name} {device.os_version} · {device.architecture}</p>
            <p className="text-slate-500 text-xs mt-1 font-mono">{device.device_uuid}</p>
          </div>
          <div className="flex flex-wrap gap-3 text-sm">
            <span className={`px-3 py-1 rounded-full font-medium ${device.is_online ? "bg-green-500/10 text-green-400 border border-green-500/20" : "bg-slate-700 text-slate-400"}`}>
              {device.is_online ? "● Online" : "○ Offline"}
            </span>
            <span className="px-3 py-1 rounded-full bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
              Agent v{device.agent_version}
            </span>
            {unresolved.length > 0 && (
              <span className="px-3 py-1 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20">
                ⚠ {unresolved.length} alert{unresolved.length !== 1 ? "s" : ""}
              </span>
            )}
          </div>
        </div>

        {/* Live metrics */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard label="CPU Usage" value={latest?.cpu_usage_percent?.toFixed(1) ?? null} unit="%" icon={Cpu}
            color={latest && (latest.cpu_usage_percent ?? 0) > 85 ? "#ef4444" : "#6366f1"} />
          <MetricCard label="RAM Usage" value={latest?.ram_usage_percent?.toFixed(1) ?? null} unit="%" icon={Activity}
            color={latest && (latest.ram_usage_percent ?? 0) > 80 ? "#ef4444" : "#22c55e"} />
          <MetricCard label="Disk Usage" value={latest?.disk_usage_percent?.toFixed(1) ?? null} unit="%" icon={HardDrive}
            color={latest && (latest.disk_usage_percent ?? 0) > 85 ? "#ef4444" : "#f59e0b"} />
          <MetricCard label="Uptime" value={fmtUptime(latest?.uptime_seconds ?? null)} icon={Clock} color="#8b5cf6" />
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard label="Upload Speed" value={fmtSpeed(latest?.upload_speed_bps ?? null)} icon={Wifi} color="#06b6d4" />
          <MetricCard label="Download Speed" value={fmtSpeed(latest?.download_speed_bps ?? null)} icon={Wifi} color="#10b981" />
          <MetricCard label="Processes" value={latest?.total_processes ?? null} icon={Activity} color="#6366f1" />
          <MetricCard label="Battery" value={latest?.battery_percent != null ? `${latest.battery_percent}` : "N/A"} unit={latest?.battery_percent != null ? "%" : ""} icon={Battery} color="#22c55e" />
        </div>

        {/* Historical charts */}
        <div className="grid lg:grid-cols-2 gap-6">
          {/* CPU + RAM area chart */}
          <div className="glass p-5">
            <h2 className="font-semibold text-white mb-4 flex items-center gap-2">
              <Cpu className="w-4 h-4 text-indigo-400" /> CPU & RAM — Last 30 Snapshots
            </h2>
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={history}>
                <defs>
                  <linearGradient id="cpuG" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="ramG" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="t" tick={{ fill: "#64748b", fontSize: 10 }} />
                <YAxis domain={[0, 100]} tick={{ fill: "#64748b", fontSize: 11 }} unit="%" />
                <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: "8px" }} labelStyle={{ color: "#94a3b8" }} />
                <Legend wrapperStyle={{ fontSize: "12px", color: "#94a3b8" }} />
                <Area type="monotone" dataKey="cpu" name="CPU %" stroke="#6366f1" fill="url(#cpuG)" strokeWidth={2} dot={false} />
                <Area type="monotone" dataKey="ram" name="RAM %" stroke="#22c55e" fill="url(#ramG)" strokeWidth={2} dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {/* Disk bar chart */}
          <div className="glass p-5">
            <h2 className="font-semibold text-white mb-4 flex items-center gap-2">
              <HardDrive className="w-4 h-4 text-amber-400" /> Disk Usage History
            </h2>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={history.slice(-15)}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="t" tick={{ fill: "#64748b", fontSize: 10 }} />
                <YAxis domain={[0, 100]} tick={{ fill: "#64748b", fontSize: 11 }} unit="%" />
                <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: "8px" }} labelStyle={{ color: "#94a3b8" }} />
                <Bar dataKey="disk" name="Disk %" fill="#f59e0b" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Network speed live chart */}
        <div className="glass p-5">
          <h2 className="font-semibold text-white mb-4 flex items-center gap-2">
            <Wifi className="w-4 h-4 text-cyan-400" /> Network Speed — Live (KB/s)
            <span className="ml-auto flex items-center gap-1.5 text-xs">
              <span className={`w-2 h-2 rounded-full ${connected ? "bg-green-400 status-dot" : "bg-slate-600"}`} />
              <span className={connected ? "text-green-400" : "text-slate-500"}>{connected ? "Live" : "Polling"}</span>
            </span>
          </h2>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={netHistory}>
              <defs>
                <linearGradient id="upG" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#06b6d4" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="downG" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="t" tick={{ fill: "#64748b", fontSize: 10 }} />
              <YAxis tick={{ fill: "#64748b", fontSize: 11 }} unit=" KB/s" width={70} />
              <Tooltip
                contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: "8px" }}
                labelStyle={{ color: "#94a3b8" }}
                formatter={(val: any) => [`${Number(val ?? 0).toFixed(2)} KB/s`]}
              />
              <Legend wrapperStyle={{ fontSize: "12px", color: "#94a3b8" }} />
              <Area type="monotone" dataKey="up" name="Upload" stroke="#06b6d4" fill="url(#upG)" strokeWidth={2} dot={false} />
              <Area type="monotone" dataKey="down" name="Download" stroke="#10b981" fill="url(#downG)" strokeWidth={2} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Alerts */}
        <div className="glass p-5">
          <h2 className="font-semibold text-white mb-4 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-400" /> Alerts
            <span className="ml-auto text-xs text-slate-500">{alerts.length} total, {unresolved.length} unresolved</span>
          </h2>
          {alerts.length === 0 ? (
            <div className="flex items-center gap-2 text-green-400 text-sm py-4">
              <CheckCircle2 className="w-5 h-5" /> No alerts for this device
            </div>
          ) : (
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {alerts.map((a) => (
                <div key={a.id} className={`flex items-start gap-3 p-4 rounded-lg border text-sm transition-opacity
                  ${a.is_resolved ? "opacity-40" : ""}
                  ${a.severity === "critical" ? "border-red-500/30 bg-red-500/5" :
                    a.severity === "warning" ? "border-amber-500/30 bg-amber-500/5" : "border-slate-700 bg-slate-800/50"}`}>
                  <AlertTriangle className={`w-4 h-4 mt-0.5 flex-shrink-0
                    ${a.severity === "critical" ? "text-red-400" : a.severity === "warning" ? "text-amber-400" : "text-slate-400"}`} />
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-white">{a.title}</p>
                    <p className="text-slate-400 text-xs mt-0.5">{a.message}</p>
                    <p className="text-slate-600 text-xs mt-1">{new Date(a.created_at).toLocaleString()}</p>
                  </div>
                  {!a.is_resolved && (
                    <button onClick={() => handleResolve(a.id)}
                      className="text-xs px-3 py-1 rounded-lg bg-slate-700 hover:bg-slate-600 text-slate-300 hover:text-white transition-colors flex-shrink-0">
                      Resolve
                    </button>
                  )}
                  {a.is_resolved && (
                    <span className="text-xs text-green-400 flex items-center gap-1 flex-shrink-0">
                      <CheckCircle2 className="w-3 h-3" /> Resolved
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
