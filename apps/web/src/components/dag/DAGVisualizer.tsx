"use client";

import React, { useEffect, useState } from "react";
import {
  GitCommit,
  CheckCircle2,
  Clock,
  ShieldAlert,
  XCircle,
  ArrowRight,
  RefreshCw,
  Terminal,
  ChevronDown,
  ChevronUp,
  Layers,
  Code,
} from "lucide-react";
import { fetchTasks, fetchTaskDetails } from "@/lib/api";

interface DAGVisualizerProps {
  selectedTaskId?: string;
}

export const DAGVisualizer: React.FC<DAGVisualizerProps> = ({ selectedTaskId }) => {
  const [tasks, setTasks] = useState<any[]>([]);
  const [activeTask, setActiveTask] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [expandedSteps, setExpandedSteps] = useState<Record<string, boolean>>({});

  const loadTasks = async () => {
    setLoading(true);
    try {
      const taskList = await fetchTasks(5);
      setTasks(taskList);
      if (selectedTaskId) {
        const details = await fetchTaskDetails(selectedTaskId);
        setActiveTask(details);
      } else if (taskList.length > 0 && !activeTask) {
        const details = await fetchTaskDetails(taskList[0].id);
        setActiveTask(details);
      }
    } catch (e) {
      console.error("Failed to load tasks", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTasks();
  }, [selectedTaskId]);

  const selectTask = async (id: string) => {
    setLoading(true);
    const details = await fetchTaskDetails(id);
    setActiveTask(details);
    setLoading(false);
  };

  const toggleStepExpanded = (stepId: string) => {
    setExpandedSteps((prev) => ({
      ...prev,
      [stepId]: !prev[stepId],
    }));
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "SUCCEEDED":
      case "COMPLETED":
        return (
          <span className="flex items-center space-x-1 text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 rounded text-[10px] font-semibold shrink-0">
            <CheckCircle2 className="w-3 h-3" />
            <span>SUCCESS</span>
          </span>
        );
      case "WAITING_APPROVAL":
        return (
          <span className="flex items-center space-x-1 text-amber-400 bg-amber-500/10 border border-amber-500/30 px-2 py-0.5 rounded text-[10px] font-semibold animate-pulse shrink-0">
            <ShieldAlert className="w-3 h-3" />
            <span>APPROVAL</span>
          </span>
        );
      case "FAILED":
        return (
          <span className="flex items-center space-x-1 text-rose-400 bg-rose-500/10 border border-rose-500/30 px-2 py-0.5 rounded text-[10px] font-semibold shrink-0">
            <XCircle className="w-3 h-3" />
            <span>FAILED</span>
          </span>
        );
      case "RUNNING":
        return (
          <span className="flex items-center space-x-1 text-cyan-300 bg-cyan-500/20 border border-cyan-400/50 px-2 py-0.5 rounded text-[10px] font-semibold animate-pulse shadow-[0_0_8px_rgba(6,182,212,0.4)] shrink-0">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping" />
            <span>RUNNING</span>
          </span>
        );
      default:
        return (
          <span className="flex items-center space-x-1 text-cyan-400 bg-cyan-500/10 border border-cyan-500/30 px-2 py-0.5 rounded text-[10px] font-semibold shrink-0">
            <Clock className="w-3 h-3" />
            <span>{status || "PLANNED"}</span>
          </span>
        );
    }
  };

  const getTaskStatusDot = (status: string) => {
    switch (status) {
      case "SUCCEEDED":
      case "COMPLETED":
        return "bg-emerald-400";
      case "FAILED":
        return "bg-rose-400";
      case "RUNNING":
        return "bg-cyan-400 animate-ping";
      default:
        return "bg-slate-400";
    }
  };

  return (
    <div className="flex flex-col h-full min-h-0 min-w-0 bg-slate-900/40 rounded-2xl border border-slate-800/80 overflow-hidden shadow-2xl backdrop-blur-sm">
      {/* Header */}
      <div className="px-4 sm:px-5 py-3 border-b border-slate-800 flex items-center justify-between bg-slate-950/40 gap-2 shrink-0">
        <div className="flex items-center space-x-2.5 min-w-0">
          <GitCommit className="w-4 h-4 text-cyan-400 shrink-0" />
          <span className="font-semibold text-xs sm:text-sm text-slate-100 truncate">DAG Execution Visualizer</span>
        </div>
        <button
          onClick={loadTasks}
          disabled={loading}
          className="min-h-[36px] min-w-[36px] p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-all flex items-center justify-center cursor-pointer active:scale-95 shrink-0"
          title="Refresh tasks"
          aria-label="Refresh tasks"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin text-cyan-400" : ""}`} />
        </button>
      </div>

      {/* Task Selector Bar */}
      <div className="px-3 sm:px-4 py-2 bg-slate-950/20 border-b border-slate-800/60 flex items-center space-x-2 overflow-x-auto scrollbar-none text-xs shrink-0 whitespace-nowrap">
        <span className="text-slate-500 shrink-0 font-medium text-[11px]">Recent Tasks:</span>
        {tasks.map((t) => (
          <button
            key={t.id}
            onClick={() => selectTask(t.id)}
            className={`px-3 py-1.5 rounded-lg shrink-0 border transition-all text-[11px] flex items-center space-x-1.5 min-h-[32px] cursor-pointer active:scale-95 ${
              activeTask?.id === t.id
                ? "bg-cyan-500/20 text-cyan-300 border-cyan-500/40 font-semibold shadow-sm"
                : "bg-slate-900 text-slate-400 border-slate-800 hover:text-slate-200 hover:bg-slate-800/60"
            }`}
          >
            <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${getTaskStatusDot(t.status)}`} />
            <span className="truncate max-w-[120px] sm:max-w-[180px]">
              {t.intent?.goal ? t.intent.goal : t.id.slice(0, 8)}
            </span>
          </button>
        ))}
        {tasks.length === 0 && <span className="text-slate-600 text-[11px]">No recent tasks found</span>}
      </div>

      {/* Main Graph Content */}
      <div className="flex-1 min-h-0 overflow-y-auto p-3 sm:p-4 space-y-3 sm:space-y-4">
        {activeTask ? (
          <div className="space-y-3 sm:space-y-4">
            {/* Task Summary Banner */}
            <div className="bg-slate-950/70 border border-slate-800 rounded-xl p-3 sm:p-3.5">
              <div className="flex items-center justify-between mb-1.5 flex-wrap gap-2">
                <span className="text-xs text-slate-400 font-medium">Goal / Intent:</span>
                {getStatusBadge(activeTask.status)}
              </div>
              <p className="text-xs sm:text-sm font-medium text-slate-200 break-words">
                {activeTask.intent?.goal || "No goal specified"}
              </p>
              <div className="flex items-center flex-wrap gap-x-4 gap-y-1 mt-2 text-[11px] text-slate-500">
                <span className="truncate max-w-[160px]">ID: {activeTask.id.slice(0, 13)}...</span>
                <span>Path: <strong className="text-cyan-400">{activeTask.path || "SMART"}</strong></span>
                <span>Steps: <strong className="text-slate-300">{activeTask.steps?.length || 0}</strong></span>
              </div>
            </div>

            {/* Steps Timeline (DAG Nodes) */}
            <div className="space-y-2.5 sm:space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-semibold text-slate-400 tracking-wide uppercase flex items-center gap-1.5">
                  <Layers className="w-3.5 h-3.5 text-cyan-400" />
                  <span>Execution Pipeline Steps</span>
                </h4>
                <span className="text-[10px] text-slate-500">
                  {activeTask.steps?.filter((s: any) => s.status === "COMPLETED" || s.status === "SUCCEEDED").length || 0} / {activeTask.steps?.length || 0} Done
                </span>
              </div>

              {activeTask.steps?.map((step: any, index: number) => {
                const stepId = step.id || String(index);
                const isExpanded = !!expandedSteps[stepId];
                const isRunning = step.status === "RUNNING";

                return (
                  <div
                    key={stepId}
                    className={`bg-slate-900/90 border rounded-xl p-3 space-y-2 transition-all min-w-0 ${
                      isRunning
                        ? "border-cyan-500/60 shadow-lg shadow-cyan-950/40 ring-1 ring-cyan-500/30"
                        : "border-slate-800/80 hover:border-slate-700"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2 flex-wrap">
                      <div className="flex items-center space-x-2 min-w-0">
                        <span className="w-5 h-5 rounded-full bg-slate-800 text-slate-400 text-[10px] font-bold flex items-center justify-center shrink-0">
                          {index + 1}
                        </span>
                        <span className="font-semibold text-xs text-slate-200 truncate">{step.step_key}</span>
                        <span className="text-[10px] px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/30 truncate shrink-0">
                          {step.capability}
                        </span>
                      </div>
                      {getStatusBadge(step.status)}
                    </div>

                    {/* Expandable Inspector Toggle */}
                    <button
                      onClick={() => toggleStepExpanded(stepId)}
                      className="w-full flex items-center justify-between pt-1 text-[11px] text-slate-400 hover:text-cyan-300 transition-colors cursor-pointer border-t border-slate-800/60 min-h-[28px]"
                    >
                      <div className="flex items-center space-x-1">
                        <Code className="w-3 h-3 text-cyan-400" />
                        <span>Inspector Details {isExpanded ? "(Hide)" : "(View Inputs / Outputs)"}</span>
                      </div>
                      {isExpanded ? (
                        <ChevronUp className="w-3.5 h-3.5" />
                      ) : (
                        <ChevronDown className="w-3.5 h-3.5" />
                      )}
                    </button>

                    {/* Inputs & Outputs Drawer / Inspector */}
                    {isExpanded && (
                      <div className="bg-slate-950/95 rounded-lg p-2.5 font-mono text-[10px] text-slate-400 space-y-1.5 overflow-x-auto border border-slate-800/80 animate-in fade-in duration-150">
                        {step.inputs && Object.keys(step.inputs).length > 0 && (
                          <div className="break-all whitespace-pre-wrap">
                            <span className="text-slate-500 font-semibold block mb-0.5">inputs:</span>
                            <pre className="text-slate-300 bg-slate-900/80 p-2 rounded overflow-x-auto max-h-36">
                              {JSON.stringify(step.inputs, null, 2)}
                            </pre>
                          </div>
                        )}
                        {step.outputs && Object.keys(step.outputs).length > 0 && (
                          <div className="break-all whitespace-pre-wrap">
                            <span className="text-emerald-400 font-semibold block mb-0.5">outputs:</span>
                            <pre className="text-emerald-300 bg-slate-900/80 p-2 rounded overflow-x-auto max-h-36">
                              {JSON.stringify(step.outputs, null, 2)}
                            </pre>
                          </div>
                        )}
                        {step.error && (
                          <div className="text-rose-400 break-all whitespace-pre-wrap">
                            <span className="font-semibold block mb-0.5">error:</span>
                            <pre className="text-rose-300 bg-rose-950/40 p-2 rounded border border-rose-500/30 overflow-x-auto max-h-36">
                              {step.error.message || JSON.stringify(step.error, null, 2)}
                            </pre>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-slate-500 text-xs space-y-2 p-6 text-center">
            <Terminal className="w-8 h-8 text-slate-600 mb-1" />
            <p className="font-medium text-slate-400">No task selected</p>
            <p className="text-[11px] text-slate-600">Execute a command in chat or pick a recent task from the bar above to visualize its DAG pipeline.</p>
          </div>
        )}
      </div>
    </div>
  );
};
export default DAGVisualizer;
