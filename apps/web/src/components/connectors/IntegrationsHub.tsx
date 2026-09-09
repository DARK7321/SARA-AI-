"use client";

import React, { useEffect, useState } from "react";
import { Mail, HardDrive, Calendar, Table, CheckCircle2, XCircle, RefreshCw, Cpu, Database, DollarSign } from "lucide-react";
import { fetchConnectors, fetchHealthCenter } from "@/lib/api";

export const IntegrationsHub: React.FC = () => {
  const [connectors, setConnectors] = useState<any[]>([]);
  const [health, setHealth] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const [conns, h] = await Promise.all([fetchConnectors(), fetchHealthCenter()]);
      setConnectors(conns);
      setHealth(h);
    } catch (e) {
      console.error("Failed to load integrations", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const getConnectorIcon = (id: string) => {
    if (id.includes("gmail")) return <Mail className="w-5 h-5 text-indigo-400" />;
    if (id.includes("drive")) return <HardDrive className="w-5 h-5 text-amber-400" />;
    if (id.includes("cal")) return <Calendar className="w-5 h-5 text-emerald-400" />;
    return <Table className="w-5 h-5 text-cyan-400" />;
  };

  return (
    <div className="h-full flex flex-col bg-slate-900/40 rounded-2xl border border-slate-800/80 overflow-hidden shadow-2xl backdrop-blur-sm">
      {/* Header */}
      <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/40">
        <div>
          <h3 className="font-semibold text-sm text-slate-100">Integrations & Health Center</h3>
          <p className="text-xs text-slate-400">Google Workspace connections, policy guards, and telemetry</p>
        </div>
        <button
          onClick={loadData}
          disabled={loading}
          className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-all"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* System Health Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 flex items-center space-x-3.5">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
              <Cpu className="w-5 h-5" />
            </div>
            <div>
              <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">FastAPI Core</span>
              <div className="text-sm font-bold text-white flex items-center space-x-1.5 mt-0.5">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                <span>v0.1.0 Healthy</span>
              </div>
            </div>
          </div>

          <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 flex items-center space-x-3.5">
            <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">PostgreSQL + Redis</span>
              <div className="text-sm font-bold text-white flex items-center space-x-1.5 mt-0.5">
                <span className="w-2 h-2 rounded-full bg-emerald-400" />
                <span>pgvector & Pool Online</span>
              </div>
            </div>
          </div>

          <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 flex items-center space-x-3.5">
            <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
              <DollarSign className="w-5 h-5" />
            </div>
            <div>
              <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Daily Spend Guard</span>
              <div className="text-sm font-bold text-white mt-0.5">
                <span>$0.000 / $5.000 Cap</span>
              </div>
            </div>
          </div>
        </div>

        {/* Installed Connectors Grid */}
        <div className="space-y-3">
          <h4 className="text-xs font-semibold text-slate-400 tracking-wide uppercase">Google Workspace Connectors</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {connectors.map((c) => (
              <div
                key={c.connector_id}
                className="bg-slate-900/90 border border-slate-800 rounded-2xl p-4 space-y-3 shadow-md"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center space-x-3">
                    <div className="w-9 h-9 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center">
                      {getConnectorIcon(c.connector_id)}
                    </div>
                    <div>
                      <h5 className="font-semibold text-sm text-slate-100">{c.name}</h5>
                      <span className="text-[11px] text-slate-500">{c.account_email || "admin@omnibrain.local"}</span>
                    </div>
                  </div>

                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold flex items-center space-x-1 ${
                      c.status === "ONLINE"
                        ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                        : "bg-slate-800 text-slate-400 border border-slate-700"
                    }`}
                  >
                    {c.status === "ONLINE" ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
                    <span>{c.status}</span>
                  </span>
                </div>

                {/* Capabilities pills */}
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {c.capabilities?.map((cap: string) => (
                    <span
                      key={cap}
                      className="px-2 py-0.5 rounded-md bg-slate-950 border border-slate-800 font-mono text-[10px] text-slate-400"
                    >
                      {cap}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

