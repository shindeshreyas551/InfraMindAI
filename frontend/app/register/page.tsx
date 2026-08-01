"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { register } from "@/lib/api";
import { Shield, Loader2, AlertCircle } from "lucide-react";

export default function RegisterPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await register(email, password, name);
      window.location.href = "/login?registered=1";
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Registration failed");
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4"
      style={{ background: "radial-gradient(ellipse at top, #1e1b4b 0%, #030712 60%)" }}>
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl mb-4"
            style={{ background: "linear-gradient(135deg, #6366f1, #8b5cf6)", boxShadow: "0 0 30px rgba(99,102,241,0.4)" }}>
            <Shield className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-white">InfraMind AI</h1>
          <p className="text-slate-400 mt-1">Create your account</p>
        </div>
        <div className="glass p-8">
          <h2 className="text-xl font-semibold text-white mb-6">New Account</h2>
          {error && (
            <div className="flex items-center gap-2 bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-3 rounded-lg mb-4 text-sm">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />{error}
            </div>
          )}
          <form onSubmit={handleSubmit} className="space-y-4">
            {[
              { label: "Full Name", type: "text", val: name, set: setName, ph: "John Doe" },
              { label: "Email", type: "email", val: email, set: setEmail, ph: "you@company.com" },
              { label: "Password", type: "password", val: password, set: setPassword, ph: "••••••••" },
            ].map(({ label, type, val, set, ph }) => (
              <div key={label}>
                <label className="block text-sm font-medium text-slate-300 mb-1">{label}</label>
                <input type={type} required value={val} onChange={(e) => set(e.target.value)}
                  className="w-full px-4 py-3 rounded-lg text-white placeholder-slate-500 outline-none"
                  style={{ background: "#0f172a", border: "1px solid #1e293b" }} placeholder={ph} />
              </div>
            ))}
            <button type="submit" disabled={loading}
              className="w-full py-3 rounded-lg font-semibold text-white flex items-center justify-center gap-2 mt-2"
              style={{ background: "linear-gradient(135deg, #6366f1, #8b5cf6)", boxShadow: "0 0 20px rgba(99,102,241,0.3)" }}>
              {loading ? <><Loader2 className="w-4 h-4 animate-spin" /> Creating...</> : "Create Account"}
            </button>
          </form>
          <p className="text-center text-slate-400 text-sm mt-6">
            Already have an account?{" "}
            <Link href="/login" className="text-indigo-400 hover:text-indigo-300 font-medium">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
