"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Shield, Users, Monitor, Cpu, Activity, AlertTriangle,
  CheckCircle2, LogOut, ArrowLeft, RefreshCw, Search,
  UserCheck, UserX, Key, Trash2, Download, ExternalLink, Sliders
} from "lucide-react";
import {
  getMe, tokenStore, getAdminDevices, Device,
  getAdminOverview, getAdminUsers, toggleDisableUser,
  deleteUser, resetUserPassword, assignDevice, exportAdminReport,
  AdminOverview, UserAdminView
} from "@/lib/api";

export default function AdminPortalPage() {
  const [me, setMe] = useState<{ id: number; email: string; full_name: string; role: string } | null>(null);
  const [overview, setOverview] = useState<AdminOverview | null>(null);
  const [users, setUsers] = useState<UserAdminView[]>([]);
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [activeTab, setActiveTab] = useState<"overview" | "users" | "devices">("overview");

  // Reset Password Modal State
  const [pwdModalUser, setPwdModalUser] = useState<UserAdminView | null>(null);
  const [newPassword, setNewPassword] = useState("");
  const [pwdStatus, setPwdStatus] = useState("");

  // Assign Device Modal State
  const [assignModalDevice, setAssignModalDevice] = useState<Device | null>(null);
  const [targetUserId, setTargetUserId] = useState<number | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const user = await getMe();
        if (user.role !== "ADMIN") {
          window.location.href = "/dashboard";
          return;
        }
        setMe(user);

        const [ovData, userData, devData] = await Promise.all([
          getAdminOverview().catch(() => null),
          getAdminUsers().catch(() => []),
          getAdminDevices().catch(() => []),
        ]);

        if (ovData) setOverview(ovData);
        setUsers(userData);
        setDevices(devData);
      } catch (err) {
        window.location.href = "/dashboard";
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    try {
      const data = await getAdminUsers(searchQuery);
      setUsers(data);
    } catch (err) {
      console.error(err);
    }
  }

  async function handleToggleDisable(userId: number) {
    try {
      const updated = await toggleDisableUser(userId);
      setUsers(users.map((u) => (u.id === userId ? updated : u)));
    } catch (err: any) {
      alert(err.message || "Failed to update user status");
    }
  }

  async function handleDeleteUser(userId: number) {
    if (!confirm("Are you sure you want to delete this user? Their devices will be unassigned.")) return;
    try {
      await deleteUser(userId);
      setUsers(users.filter((u) => u.id !== userId));
    } catch (err: any) {
      alert(err.message || "Failed to delete user");
    }
  }

  async function handleResetPassword(e: React.FormEvent) {
    e.preventDefault();
    if (!pwdModalUser || !newPassword) return;
    try {
      await resetUserPassword(pwdModalUser.id, newPassword);
      setPwdStatus(`Password reset successfully for ${pwdModalUser.email}`);
      setTimeout(() => {
        setPwdModalUser(null);
        setNewPassword("");
        setPwdStatus("");
      }, 1500);
    } catch (err: any) {
      setPwdStatus(err.message || "Failed to reset password");
    }
  }

  async function handleAssignDevice(e: React.FormEvent) {
    e.preventDefault();
    if (!assignModalDevice || !targetUserId) return;
    try {
      const updated = await assignDevice(assignModalDevice.device_uuid, targetUserId);
      setDevices(devices.map((d) => (d.device_uuid === assignModalDevice.device_uuid ? updated : d)));
      setAssignModalDevice(null);
    } catch (err: any) {
      alert(err.message || "Failed to assign device");
    }
  }

  async function handleExportReport() {
    try {
      const report = await exportAdminReport();
      const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `InfraMind_Executive_Report_${new Date().toISOString().split("T")[0]}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      alert("Failed to export compliance report: " + err.message);
    }
  }

  function logout() {
    tokenStore.clear();
    window.location.href = "/login";
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center text-white">
        <div className="flex items-center gap-3">
          <RefreshCw className="w-6 h-6 animate-spin text-indigo-500" />
          <span className="font-semibold text-slate-300">Loading Enterprise Admin Portal...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Navbar */}
      <header className="border-b border-indigo-500/20 bg-slate-950/80 backdrop-blur sticky top-0 z-40 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/dashboard" className="p-2 text-slate-400 hover:text-white bg-slate-900 border border-slate-800 rounded-xl transition-all">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div className="flex items-center gap-2">
            <Shield className="w-6 h-6 text-indigo-500" />
            <h1 className="text-xl font-bold bg-gradient-to-r from-indigo-400 via-purple-300 to-pink-400 bg-clip-text text-transparent">
              InfraMind Executive Admin Portal
            </h1>
            <span className="px-2 py-0.5 text-xs font-bold bg-indigo-500/20 border border-indigo-500/30 text-indigo-300 rounded-full">
              SUPERUSER
            </span>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <button
            onClick={handleExportReport}
            className="px-3.5 py-2 text-xs font-semibold bg-emerald-600/20 border border-emerald-500/40 text-emerald-300 hover:bg-emerald-600/30 rounded-xl transition-all flex items-center gap-1.5"
          >
            <Download className="w-3.5 h-3.5" /> Export Audit Report
          </button>
          <span className="text-sm text-slate-400">{me?.email}</span>
          <button onClick={logout} className="p-2 text-slate-400 hover:text-red-400 transition-colors">
            <LogOut className="w-5 h-5" />
          </button>
        </div>
      </header>

      <div className="max-w-7xl mx-auto p-6 space-y-6 flex-1 w-full">
        {/* Navigation Tabs */}
        <div className="flex border-b border-slate-800 gap-6">
          <button
            onClick={() => setActiveTab("overview")}
            className={`pb-3 font-semibold text-sm transition-all flex items-center gap-2 border-b-2 ${
              activeTab === "overview" ? "border-indigo-500 text-indigo-400" : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <Activity className="w-4 h-4" /> Overview Dashboard
          </button>
          <button
            onClick={() => setActiveTab("users")}
            className={`pb-3 font-semibold text-sm transition-all flex items-center gap-2 border-b-2 ${
              activeTab === "users" ? "border-indigo-500 text-indigo-400" : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <Users className="w-4 h-4" /> User Management ({users.length})
          </button>
          <button
            onClick={() => setActiveTab("devices")}
            className={`pb-3 font-semibold text-sm transition-all flex items-center gap-2 border-b-2 ${
              activeTab === "devices" ? "border-indigo-500 text-indigo-400" : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <Monitor className="w-4 h-4" /> Global Endpoints ({devices.length})
          </button>
        </div>

        {/* Tab 1: Overview */}
        {activeTab === "overview" && overview && (
          <div className="space-y-6">
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="glass p-5 flex items-center gap-4">
                <div className="p-3 bg-indigo-500/20 rounded-2xl text-indigo-400">
                  <Users className="w-6 h-6" />
                </div>
                <div>
                  <p className="text-xs text-slate-400 font-semibold">Total Accounts</p>
                  <p className="text-2xl font-bold text-white">{overview.total_users}</p>
                </div>
              </div>

              <div className="glass p-5 flex items-center gap-4">
                <div className="p-3 bg-green-500/20 rounded-2xl text-green-400">
                  <CheckCircle2 className="w-6 h-6" />
                </div>
                <div>
                  <p className="text-xs text-slate-400 font-semibold">Online Endpoints</p>
                  <p className="text-2xl font-bold text-white">{overview.online_devices} / {overview.total_devices}</p>
                </div>
              </div>

              <div className="glass p-5 flex items-center gap-4">
                <div className="p-3 bg-amber-500/20 rounded-2xl text-amber-400">
                  <Cpu className="w-6 h-6" />
                </div>
                <div>
                  <p className="text-xs text-slate-400 font-semibold">Avg CPU Load</p>
                  <p className="text-2xl font-bold text-white">{overview.avg_cpu_percent}%</p>
                </div>
              </div>

              <div className="glass p-5 flex items-center gap-4">
                <div className="p-3 bg-red-500/20 rounded-2xl text-red-400">
                  <AlertTriangle className="w-6 h-6" />
                </div>
                <div>
                  <p className="text-xs text-slate-400 font-semibold">Unresolved Alerts</p>
                  <p className="text-2xl font-bold text-white">{overview.unresolved_alerts}</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: User Management */}
        {activeTab === "users" && (
          <div className="space-y-4">
            <form onSubmit={handleSearch} className="flex gap-3 max-w-md">
              <div className="relative flex-1">
                <Search className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
                <input
                  type="text"
                  placeholder="Search user email or full name..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-9 pr-4 py-2 bg-slate-900 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-indigo-500"
                />
              </div>
              <button type="submit" className="px-4 py-2 bg-indigo-600 text-xs font-semibold text-white rounded-xl hover:bg-indigo-500">
                Search
              </button>
            </form>

            <div className="glass overflow-hidden">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-900/60 text-slate-400 border-b border-slate-800">
                  <tr>
                    <th className="p-4">User</th>
                    <th className="p-4">Role</th>
                    <th className="p-4">Status</th>
                    <th className="p-4">Endpoints</th>
                    <th className="p-4">Registered</th>
                    <th className="p-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/50">
                  {users.map((u) => (
                    <tr key={u.id} className="hover:bg-slate-900/40">
                      <td className="p-4 font-medium text-white">
                        <div>{u.full_name || "N/A"}</div>
                        <div className="text-xs text-slate-400">{u.email}</div>
                      </td>
                      <td className="p-4">
                        <span className={`text-xs px-2.5 py-1 rounded-full font-semibold ${u.role === "ADMIN" ? "bg-indigo-500/20 text-indigo-300" : "bg-slate-800 text-slate-300"}`}>
                          {u.role}
                        </span>
                      </td>
                      <td className="p-4">
                        <span className={`text-xs px-2 py-1 rounded-full font-medium ${u.is_active ? "bg-green-500/10 text-green-400" : "bg-red-500/10 text-red-400"}`}>
                          {u.is_active ? "Active" : "Disabled"}
                        </span>
                      </td>
                      <td className="p-4 font-semibold text-slate-300">{u.device_count}</td>
                      <td className="p-4 text-xs text-slate-400">{u.created_at.split("T")[0]}</td>
                      <td className="p-4 text-right space-x-2">
                        <button
                          onClick={() => handleToggleDisable(u.id)}
                          title={u.is_active ? "Disable User" : "Enable User"}
                          className={`p-1.5 rounded-lg border transition-colors ${u.is_active ? "bg-amber-500/10 border-amber-500/30 text-amber-400 hover:bg-amber-500/20" : "bg-green-500/10 border-green-500/30 text-green-400 hover:bg-green-500/20"}`}
                        >
                          {u.is_active ? <UserX className="w-4 h-4" /> : <UserCheck className="w-4 h-4" />}
                        </button>
                        <button
                          onClick={() => setPwdModalUser(u)}
                          title="Reset Password"
                          className="p-1.5 bg-indigo-500/10 border border-indigo-500/30 text-indigo-400 hover:bg-indigo-500/20 rounded-lg transition-colors"
                        >
                          <Key className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleDeleteUser(u.id)}
                          title="Delete User"
                          className="p-1.5 bg-red-500/10 border border-red-500/30 text-red-400 hover:bg-red-500/20 rounded-lg transition-colors"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Tab 3: Global Devices */}
        {activeTab === "devices" && (
          <div className="glass overflow-hidden">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-900/60 text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="p-4">Hostname / UUID</th>
                  <th className="p-4">OS / Arch</th>
                  <th className="p-4">MAC / IP Address</th>
                  <th className="p-4">Status</th>
                  <th className="p-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/50">
                {devices.map((d) => (
                  <tr key={d.id} className="hover:bg-slate-900/40">
                    <td className="p-4">
                      <div className="font-semibold text-white">{d.display_name || d.hostname}</div>
                      <div className="text-xs text-slate-500 font-mono">{d.device_uuid}</div>
                    </td>
                    <td className="p-4 text-xs text-slate-400">{d.os_name} · {d.architecture}</td>
                    <td className="p-4 text-xs font-mono text-slate-400">
                      <div>{d.mac_address || "N/A"}</div>
                      <div className="text-slate-500">{d.ip_address || "N/A"}</div>
                    </td>
                    <td className="p-4">
                      <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${d.is_online ? "bg-green-500/10 text-green-400" : "bg-slate-800 text-slate-400"}`}>
                        {d.is_online ? "Online" : "Offline"}
                      </span>
                    </td>
                    <td className="p-4 text-right space-x-2">
                      <button
                        onClick={() => setAssignModalDevice(d)}
                        className="px-2.5 py-1 text-xs bg-indigo-600/20 border border-indigo-500/40 text-indigo-300 hover:bg-indigo-600/30 rounded-lg transition-colors"
                      >
                        Assign User
                      </button>
                      <Link
                        href={`/devices/${d.device_uuid}`}
                        className="p-1.5 inline-block bg-slate-800 text-slate-300 hover:text-white rounded-lg transition-colors"
                      >
                        <ExternalLink className="w-4 h-4" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Password Reset Modal */}
      {pwdModalUser && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <form onSubmit={handleResetPassword} className="glass p-6 max-w-sm w-full space-y-4">
            <h3 className="text-lg font-bold text-white">Reset User Password</h3>
            <p className="text-xs text-slate-400">Set new password for <span className="text-indigo-400 font-medium">{pwdModalUser.email}</span></p>
            <input
              type="password"
              placeholder="New password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
              className="w-full px-4 py-2.5 bg-slate-900 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-indigo-500"
            />
            {pwdStatus && <p className="text-xs text-indigo-400">{pwdStatus}</p>}
            <div className="flex gap-3 justify-end">
              <button type="button" onClick={() => setPwdModalUser(null)} className="px-4 py-2 text-xs bg-slate-800 text-slate-300 rounded-xl hover:bg-slate-700">Cancel</button>
              <button type="submit" className="px-4 py-2 text-xs bg-indigo-600 text-white font-semibold rounded-xl hover:bg-indigo-500">Reset</button>
            </div>
          </form>
        </div>
      )}

      {/* Assign Device Modal */}
      {assignModalDevice && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <form onSubmit={handleAssignDevice} className="glass p-6 max-w-sm w-full space-y-4">
            <h3 className="text-lg font-bold text-white">Assign Device to User</h3>
            <p className="text-xs text-slate-400">Select owner account for endpoint <span className="text-indigo-400 font-mono">{assignModalDevice.hostname}</span></p>
            <select
              onChange={(e) => setTargetUserId(Number(e.target.value))}
              required
              className="w-full px-4 py-2.5 bg-slate-900 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-indigo-500"
            >
              <option value="">Select User...</option>
              {users.map((u) => (
                <option key={u.id} value={u.id}>{u.email} ({u.full_name || "User"})</option>
              ))}
            </select>
            <div className="flex gap-3 justify-end">
              <button type="button" onClick={() => setAssignModalDevice(null)} className="px-4 py-2 text-xs bg-slate-800 text-slate-300 rounded-xl hover:bg-slate-700">Cancel</button>
              <button type="submit" className="px-4 py-2 text-xs bg-indigo-600 text-white font-semibold rounded-xl hover:bg-indigo-500">Assign</button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
