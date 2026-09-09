"use client";

import React, { useEffect, useState } from "react";
import {
  Shield,
  ShieldAlert,
  AlertTriangle,
  Zap,
  CheckCircle,
  Activity,
  RotateCcw,
  Plus,
  Trash2,
  Play,
  Terminal,
  Cpu,
} from "lucide-react";
import {
  fetchAutonomySettings,
  updateAutonomyLevel,
  fetchSafetyStatus,
  toggleKillSwitch,
  resetCircuitBreaker,
  fetchAliases,
  createAlias,
  deleteAlias,
  AutonomySettingsData,
  SafetyStatusData,
  AliasItem,
  runWorkflow,
} from "@/lib/api";

export const AutonomySettingsHub: React.FC = () => {
  const [autonomyData, setAutonomyData] = useState<AutonomySettingsData | null>(null);
  const [safetyData, setSafetyData] = useState<SafetyStatusData | null>(null);
  const [aliases, setAliases] = useState<AliasItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [savingLevel, setSavingLevel] = useState(false);
  const [killLoading, setKillLoading] = useState(false);
  const [resetLoading, setResetLoading] = useState<string | null>(null);

  // New alias modal state
  const [showAddAlias, setShowAddAlias] = useState(false);
  const [newAliasName, setNewAliasName] = useState("");
  const [newAliasTarget, setNewAliasTarget] = useState("Morning Standup Briefing");

  const loadAll = async () => {
    try {
      const [auto, safe, aliasList] = await Promise.all([
        fetchAutonomySettings(),
        fetchSafetyStatus(),
        fetchAliases(),
      ]);
      if (auto) setAutonomyData(auto);
      if (safe) setSafetyData(safe);
      setAliases(aliasList);
    } catch {
      // quiet fallback
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
    const interval = setInterval(loadAll, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleSelectLevel = async (level: number) => {
    setSavingLevel(true);
    try {
      const ok = await updateAutonomyLevel(level);
      if (ok) {
        await loadAll();
      }
    } finally {
      setSavingLevel(false);
    }
  };

  const handleToggleKill = async () => {
    if (!safetyData) return;
    const currentState = safetyData.kill_switch.active;
    setKillLoading(true);
    try {
      await toggleKillSwitch(!currentState, currentState ? undefined : "Manual user emergency stop");
      await loadAll();
    } finally {
      setKillLoading(false);
    }
  };

  const handleResetBreaker = async (connectorName?: string) => {
    setResetLoading(connectorName || "all");
    try {
      await resetCircuitBreaker(connectorName);
      await loadAll();
    } finally {
      setResetLoading(null);
    }
  };

  const handleCreateAlias = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newAliasName.trim()) return;
    try {
      await createAlias({
        name: newAliasName.trim().toLowerCase(),
        target_type: "workflow",
        target_id: newAliasTarget,
      });
      setNewAliasName("");
      setShowAddAlias(false);
      await loadAll();
    } catch (err: any) {
      alert(err.message || "Failed to create alias");
    }
  };

  const handleDeleteAlias = async (id: string) => {
    if (!confirm("Are you sure you want to delete this shortcut alias?")) return;
    await deleteAlias(id);
    await loadAll();
  };

  if (loading && !autonomyData) {
    return (
      <div className="flex items-center justify-center h-full text-slate-400 space-x-2">
        <Activity className="w-5 h-5 animate-spin text-cyan-400" />
        <span>Loading Autonomy & Safety controls...</span>
      </div>
    );
  }

  const currentLevel = autonomyData?.current_level ?? 2;
  const isKilled = safetyData?.kill_switch?.active ?? false;
  const circuitHealthy = safetyData?.circuit_breakers?.system_circuit_healthy ?? true;

  return (
    <div className="h-full overflow-y-auto space-y-8 pr-2 pb-10">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-xl font-bold text-white tracking-wide">
              Safety, Progressive Autonomy & Aliases
            </h1>
            <span className="bg-indigo-500/20 text-indigo-300 text-xs px-2.5 py-0.5 rounded-full border border-indigo-500/30">
              Phase 8 Hardened
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Deterministic security governance, progressive autonomy levels (0 to 4), emergency stop, and instant shortcuts.
          </p>
        </div>

        {/* Global Emergency Kill Switch Button */}
        <button
          onClick={handleToggleKill}
          disabled={killLoading}
          className={`flex items-center space-x-2 px-5 py-2.5 rounded-xl font-bold text-xs tracking-wider transition-all cursor-pointer shadow-lg ${
            isKilled
              ? "bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-600/30 animate-pulse"
              : "bg-rose-600 hover:bg-rose-500 text-white shadow-rose-600/30"
          }`}
        >
          <ShieldAlert className="w-4 h-4" />
          <span>{isKilled ? "RESUME SYSTEM OPERATIONS" : "EMERGENCY KILL SWITCH"}</span>
        </button>
      </div>

      {/* 1. Progressive Autonomy Level Selector */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Shield className="w-4 h-4 text-cyan-400" />
            <h2 className="text-sm font-semibold text-white uppercase tracking-wider">
              Progressive Autonomy Levels (0 → 4)
            </h2>
          </div>
          <span className="text-xs text-slate-400">
            Current Level: <strong className="text-cyan-300">Level {currentLevel}</strong>
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
          {[0, 1, 2, 3, 4].map((lvl) => {
            const tier = autonomyData?.tiers[lvl] || {
              title: `Level ${lvl}`,
              description: "",
              badge: "",
              color: "cyan",
            };
            const isSelected = currentLevel === lvl;

            return (
              <div
                key={lvl}
                onClick={() => !savingLevel && handleSelectLevel(lvl)}
                className={`p-4 rounded-xl border transition-all cursor-pointer relative flex flex-col justify-between ${
                  isSelected
                    ? "bg-slate-900 border-cyan-500 shadow-lg shadow-cyan-500/10 ring-1 ring-cyan-500"
                    : "bg-slate-900/40 border-slate-800 hover:border-slate-700 hover:bg-slate-900/80"
                }`}
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-bold text-slate-400">L{lvl}</span>
                    <span
                      className={`text-[10px] px-2 py-0.5 rounded font-semibold ${
                        isSelected
                          ? "bg-cyan-500 text-slate-950"
                          : "bg-slate-800 text-slate-300"
                      }`}
                    >
                      {tier.badge}
                    </span>
                  </div>
                  <h3 className="text-xs font-bold text-white mb-1.5">{tier.title}</h3>
                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    {tier.description}
                  </p>
                </div>

                <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-[10px]">
                  <span className="text-slate-500">
                    {lvl === 2 ? "Recommended" : lvl === 0 ? "Zero-Trust" : lvl === 4 ? "Full-Auto" : "Standard"}
                  </span>
                  {isSelected && (
                    <span className="text-cyan-400 font-semibold flex items-center space-x-1">
                      <CheckCircle className="w-3 h-3" />
                      <span>Active</span>
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 2. Circuit Breakers & Anomaly Telemetry */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Cpu className="w-4 h-4 text-emerald-400" />
            <h2 className="text-sm font-semibold text-white uppercase tracking-wider">
              Connector Circuit Breakers & Health
            </h2>
          </div>
          <button
            onClick={() => handleResetBreaker()}
            disabled={resetLoading !== null}
            className="flex items-center space-x-1 px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs rounded-lg transition-all cursor-pointer"
          >
            <RotateCcw className="w-3 h-3" />
            <span>Reset All Breakers</span>
          </button>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {Object.entries(safetyData?.circuit_breakers?.connectors || {}).map(([name, breaker]) => {
            const isTripped = breaker.state === "OPEN";
            return (
              <div
                key={name}
                className={`p-3.5 rounded-xl border flex flex-col justify-between ${
                  isTripped
                    ? "bg-rose-950/20 border-rose-500/50"
                    : "bg-slate-900/60 border-slate-800"
                }`}
              >
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="font-semibold text-xs text-white capitalize">{name}</span>
                    <span
                      className={`text-[9px] font-bold px-2 py-0.5 rounded uppercase ${
                        isTripped
                          ? "bg-rose-500 text-white animate-pulse"
                          : "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                      }`}
                    >
                      {breaker.state}
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-400 space-y-0.5">
                    <p>Total Calls: <span className="text-slate-200">{breaker.total_calls}</span></p>
                    <p>Consecutive Errors: <span className={breaker.consecutive_failures > 0 ? "text-amber-400 font-bold" : "text-slate-200"}>{breaker.consecutive_failures}</span></p>
                    {breaker.last_error && (
                      <p className="text-[10px] text-rose-300 truncate mt-1" title={breaker.last_error}>
                        Error: {breaker.last_error}
                      </p>
                    )}
                  </div>
                </div>

                {isTripped && (
                  <button
                    onClick={() => handleResetBreaker(name)}
                    disabled={resetLoading === name}
                    className="mt-3 w-full py-1 bg-rose-600 hover:bg-rose-500 text-white text-[10px] font-bold rounded-lg transition-all"
                  >
                    Reset Breaker
                  </button>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* 3. Natural Language Aliases */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Terminal className="w-4 h-4 text-amber-400" />
            <h2 className="text-sm font-semibold text-white uppercase tracking-wider">
              Natural Language Voice & Text Aliases
            </h2>
          </div>
          <button
            onClick={() => setShowAddAlias(true)}
            className="flex items-center space-x-1 px-3 py-1.5 bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-bold text-xs rounded-lg transition-all cursor-pointer shadow-sm"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>New Custom Alias</span>
          </button>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/60 border-b border-slate-800 text-slate-400 uppercase text-[10px] tracking-wider">
              <tr>
                <th className="px-4 py-3">Trigger Phrase</th>
                <th className="px-4 py-3">Target Action / Workflow</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-300">
              {aliases.map((alias) => (
                <tr key={alias.id} className="hover:bg-slate-800/30 transition-colors">
                  <td className="px-4 py-3 font-mono font-bold text-cyan-400">
                    &quot;{alias.name}&quot;
                  </td>
                  <td className="px-4 py-3">
                    <span className="font-semibold text-white">{alias.target_id || "Direct Action"}</span>
                    {alias.description && (
                      <p className="text-[10px] text-slate-500">{alias.description}</p>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <span className="bg-slate-800 text-slate-300 px-2 py-0.5 rounded text-[10px] uppercase">
                      {alias.target_type}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right space-x-2">
                    {!alias.is_builtin && (
                      <button
                        onClick={() => handleDeleteAlias(alias.id)}
                        className="text-slate-500 hover:text-rose-400 transition-colors p-1"
                        title="Delete custom alias"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add Alias Modal */}
      {showAddAlias && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <h3 className="text-base font-bold text-white">Create Custom Voice / Chat Alias</h3>
            <form onSubmit={handleCreateAlias} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">
                  Trigger Phrase or Keyword (e.g. &quot;daily&quot;, &quot;standup&quot;)
                </label>
                <input
                  type="text"
                  value={newAliasName}
                  onChange={(e) => setNewAliasName(e.target.value)}
                  placeholder="e.g. standup"
                  required
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">
                  Target Workflow
                </label>
                <select
                  value={newAliasTarget}
                  onChange={(e) => setNewAliasTarget(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white outline-none focus:border-cyan-500"
                >
                  <option value="Morning Standup Briefing">Morning Standup Briefing</option>
                  <option value="GitHub Issue & PR Triage">GitHub Issue & PR Triage</option>
                  <option value="Web Intelligence Digest">Web Intelligence Digest</option>
                </select>
              </div>

              <div className="flex items-center justify-end space-x-2 pt-3">
                <button
                  type="button"
                  onClick={() => setShowAddAlias(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs rounded-xl"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-xs rounded-xl shadow-md shadow-cyan-500/20"
                >
                  Create Alias
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

