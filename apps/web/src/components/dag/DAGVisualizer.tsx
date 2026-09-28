"use client";

import React, { useEffect, useState } from "react";
import { GitCommit, CheckCircle2, Clock, ShieldAlert, XCircle, ArrowDown, RefreshCw, Terminal } from "lucide-react";
import { fetchTasks, fetchTaskDetails } from "@/lib/api";

interface DAGVisualizerProps {
  selectedTaskId?: string;
  taskEventTimestamp?: number;
}

export const DAGVisualizer: React.FC<DAGVisualizerProps> = ({ selectedTaskId, taskEventTimestamp }) => {
  const [tasks, setTasks] = useState<any[]>([]);
  const [activeTask, setActiveTask] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const loadTasks = async (targetId?: string) => {
    setLoading(true);
    try {
      const taskList = await fetchTasks(10);
      setTasks(taskList);
      const idToFetch = targetId || selectedTaskId;
      if (idToFetch) {
        const details = await fetchTaskDetails(idToFetch);
        if (details) setActiveTask(details);
      } else if (taskList.length > 0 && (!activeTask || !taskList.some((t) => t.id === activeTask.id))) {
        const details = await fetchTaskDetails(taskList[0].id);
        if (details) setActiveTask(details);
      }
    } catch (e) {
      console.error("Failed to load tasks", e);
    } finally {
      setLoading(false);
    }
  };

  // Reload when selectedTaskId changes or a chat task event occurs
  useEffect(() => {
    loadTasks(selectedTaskId);
  }, [selectedTaskId, taskEventTimestamp]);

  // Live polling for tasks in progress (PLANNED, RUNNING, EXECUTING, WAITING_APPROVAL)
  useEffect(() => {
    if (!activeTask?.id) return;
    const status = (activeTask.status || "").toUpperCase();
    const isFinished = ["SUCCEEDED", "COMPLETED", "FAILED", "CANCELLED"].includes(status);
    if (isFinished) return;

    const timer = setInterval(async () => {
      try {
        const details = await fetchTaskDetails(activeTask.id);
        if (details) {
          setActiveTask(details);
          const newStatus = (details.status || "").toUpperCase();
          if (["SUCCEEDED", "COMPLETED", "FAILED", "CANCELLED"].includes(newStatus)) {
            // Task just completed! Refresh recent tasks list
            const freshList = await fetchTasks(10);
            setTasks(freshList);
          }
        }
      } catch (err) {
        console.error("Polling task failed:", err);
      }
    }, 1000);

    return () => clearInterval(timer);
  }, [activeTask?.id, activeTask?.status]);

  const selectTask = async (id: string) => {
    setLoading(true);
    try {
      const details = await fetchTaskDetails(id);
      if (details) setActiveTask(details);
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const s = (status || "").toUpperCase();
    switch (s) {
      case "SUCCEEDED":
      case "COMPLETED":
        return (
          <span className="flex items-center space-x-1 text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 rounded text-[10px] font-semibold">
            <CheckCircle2 className="w-3 h-3" />
            <span>SUCCESS</span>
          </span>
        );
      case "WAITING_APPROVAL":
        return (
          <span className="flex items-center space-x-1 text-amber-400 bg-amber-500/10 border border-amber-500/30 px-2 py-0.5 rounded text-[10px] font-semibold animate-pulse">
            <ShieldAlert className="w-3 h-3" />
            <span>APPROVAL NEEDED</span>
          </span>
        );
      case "RUNNING":
      case "EXECUTING":
      case "IN_PROGRESS":
        return (
          <span className="flex items-center space-x-1 text-cyan-400 bg-cyan-500/10 border border-cyan-500/30 px-2 py-0.5 rounded text-[10px] font-semibold animate-pulse">
            <RefreshCw className="w-3 h-3 animate-spin text-cyan-400" />
            <span>RUNNING</span>
          </span>
        );
      case "FAILED":
        return (
          <span className="flex items-center space-x-1 text-rose-400 bg-rose-500/10 border border-rose-500/30 px-2 py-0.5 rounded text-[10px] font-semibold">
            <XCircle className="w-3 h-3" />
            <span>FAILED</span>
          </span>
        );
      case "CANCELLED":
        return (
          <span className="flex items-center space-x-1 text-slate-400 bg-slate-800 border border-slate-700 px-2 py-0.5 rounded text-[10px] font-semibold">
            <XCircle className="w-3 h-3 text-slate-400" />
            <span>CANCELLED</span>
          </span>
        );
      default:
        return (
          <span className="flex items-center space-x-1 text-cyan-400 bg-cyan-500/10 border border-cyan-500/30 px-2 py-0.5 rounded text-[10px] font-semibold">
            <Clock className="w-3 h-3" />
            <span>{s || "PLANNED"}</span>
          </span>
        );
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-900/40 rounded-2xl border border-slate-800/80 overflow-hidden shadow-2xl backdrop-blur-sm">
      {/* Header */}
      <div className="px-5 py-3.5 border-b border-slate-800 flex items-center justify-between bg-slate-950/40">
        <div className="flex items-center space-x-2.5">
          <GitCommit className="w-4 h-4 text-cyan-400" />
          <span className="font-semibold text-sm text-slate-100">DAG Execution Visualizer</span>
          {activeTask && (
            <span className="text-[10px] text-slate-500 font-mono">
              #{activeTask.id.slice(0, 8)}
            </span>
          )}
        </div>
        <button
          onClick={() => loadTasks(activeTask?.id)}
          disabled={loading}
          className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-all cursor-pointer"
          title="Refresh tasks"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {/* Task Selector Bar */}
      <div className="px-4 py-2 bg-slate-950/20 border-b border-slate-800/60 flex items-center space-x-2 overflow-x-auto text-xs scrollbar-none">
        <span className="text-slate-500 shrink-0 font-medium text-[11px]">Recent Tasks:</span>
        {tasks.map((t) => {
          const isActive = activeTask?.id === t.id;
          const status = (t.status || "").toUpperCase();
          return (
            <button
              key={t.id}
              onClick={() => selectTask(t.id)}
              className={`px-3 py-1 rounded-lg shrink-0 border transition-all text-[11px] flex items-center space-x-1.5 cursor-pointer ${
                isActive
                  ? "bg-cyan-500/20 text-cyan-300 border-cyan-500/40 font-semibold shadow-sm"
                  : "bg-slate-900 text-slate-400 border-slate-800 hover:text-slate-200 hover:border-slate-700"
              }`}
            >
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  status === "SUCCEEDED" || status === "COMPLETED"
                    ? "bg-emerald-400"
                    : status === "FAILED"
                    ? "bg-rose-400"
                    : status === "RUNNING" || status === "EXECUTING"
                    ? "bg-cyan-400 animate-pulse"
                    : "bg-slate-500"
                }`}
              />
              <span>{t.intent?.goal ? t.intent.goal.slice(0, 24) + (t.intent.goal.length > 24 ? "..." : "") : t.id.slice(0, 8)}</span>
            </button>
          );
        })}
        {tasks.length === 0 && <span className="text-slate-600 text-[11px]">No recent tasks found</span>}
      </div>

      {/* Main Graph Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {activeTask ? (
          <div className="space-y-4">
            {/* Task Summary Banner */}
            <div className="bg-slate-950/70 border border-slate-800 rounded-xl p-3.5">
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs text-slate-400 font-medium">Goal:</span>
                {getStatusBadge(activeTask.status)}
              </div>
              <p className="text-sm font-medium text-slate-200">{activeTask.intent?.goal || "No goal specified"}</p>
              <div className="flex items-center space-x-4 mt-2 text-[11px] text-slate-500">
                <span>Task ID: <code className="text-slate-400">{activeTask.id.slice(0, 13)}...</code></span>
                <span>Path: <strong className="text-cyan-400">{activeTask.path || "SMART"}</strong></span>
                <span>Steps: <strong className="text-slate-300">{activeTask.steps?.length || 0}</strong></span>
              </div>
            </div>

            {/* Steps Timeline (DAG Nodes with connecting arrows) */}
            <div className="space-y-1">
              <h4 className="text-xs font-semibold text-slate-400 tracking-wide uppercase mb-3">Execution Pipeline</h4>
              {activeTask.steps?.map((step: any, index: number) => {
                const stepStatus = (step.status || "").toUpperCase();
                const isRunning = stepStatus === "RUNNING" || stepStatus === "EXECUTING";
                const isSuccess = stepStatus === "SUCCEEDED" || stepStatus === "COMPLETED";
                const isFailed = stepStatus === "FAILED";

                return (
                  <React.Fragment key={step.id || index}>
                    <div
                      className={`bg-slate-900/90 border rounded-xl p-3.5 space-y-2 relative transition-all ${
                        isRunning
                          ? "border-cyan-500/60 shadow-lg shadow-cyan-500/10 ring-1 ring-cyan-500/30"
                          : isSuccess
                          ? "border-emerald-500/30 bg-emerald-950/10"
                          : isFailed
                          ? "border-rose-500/30 bg-rose-950/10"
                          : "border-slate-800/80"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          <span
                            className={`w-5 h-5 rounded-full text-[10px] font-bold flex items-center justify-center ${
                              isSuccess
                                ? "bg-emerald-500/20 text-emerald-400"
                                : isRunning
                                ? "bg-cyan-500/20 text-cyan-400 animate-pulse"
                                : "bg-slate-800 text-slate-400"
                            }`}
                          >
                            {index + 1}
                          </span>
                          <span className="font-semibold text-xs text-slate-200">{step.step_key}</span>
                          <span className="text-[10px] px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/30 font-mono">
                            {step.capability}
                          </span>
                        </div>
                        {getStatusBadge(step.status)}
                      </div>

                      {/* Inputs & Outputs viewer */}
                      <div className="bg-slate-950/90 rounded-lg p-2.5 font-mono text-[10px] text-slate-400 space-y-1 border border-slate-900">
                        {step.inputs && Object.keys(step.inputs).length > 0 && (
                          <div className="truncate">
                            <span className="text-slate-500">inputs: </span>
                            <span className="text-slate-300">{JSON.stringify(step.inputs)}</span>
                          </div>
                        )}
                        {step.outputs && Object.keys(step.outputs).length > 0 && (
                          <div className="truncate">
                            <span className="text-emerald-400">outputs: </span>
                            <span className="text-emerald-200">{JSON.stringify(step.outputs)}</span>
                          </div>
                        )}
                        {step.error && (
                          <div className="text-rose-400">
                            <span>error: </span>
                            <span>{step.error.message || JSON.stringify(step.error)}</span>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* DAG Arrow between nodes */}
                    {index < activeTask.steps.length - 1 && (
                      <div className="flex justify-center py-1">
                        <div className="flex flex-col items-center">
                          <div className="w-0.5 h-2 bg-slate-700/60" />
                          <ArrowDown className="w-3 h-3 text-slate-500" />
                        </div>
                      </div>
                    )}
                  </React.Fragment>
                );
              })}
            </div>
          </div>
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-slate-500 text-xs space-y-3 p-8 text-center">
            <div className="w-12 h-12 rounded-2xl bg-slate-800/60 border border-slate-700/60 flex items-center justify-center text-cyan-400 shadow-inner">
              <Terminal className="w-6 h-6 text-slate-400" />
            </div>
            <p className="font-medium text-slate-300 text-sm">No task selected</p>
            <p className="text-slate-500 max-w-xs text-[11px] leading-relaxed">
              Give Sara an instruction in chat (e.g. &quot;Check my calendar&quot; or &quot;Send email&quot;) to visualize its live execution pipeline and steps here.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
