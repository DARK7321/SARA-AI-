"use client";

import React, { useEffect, useState } from "react";
import { GitCommit, CheckCircle2, Clock, ShieldAlert, XCircle, ArrowRight, RefreshCw, Terminal } from "lucide-react";
import { fetchTasks, fetchTaskDetails } from "@/lib/api";

interface DAGVisualizerProps {
  selectedTaskId?: string;
}

export const DAGVisualizer: React.FC<DAGVisualizerProps> = ({ selectedTaskId }) => {
  const [tasks, setTasks] = useState<any[]>([]);
  const [activeTask, setActiveTask] = useState<any>(null);
  const [loading, setLoading] = useState(false);

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

  const getStatusBadge = (status: string) => {
    switch (status) {
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
      case "FAILED":
        return (
          <span className="flex items-center space-x-1 text-rose-400 bg-rose-500/10 border border-rose-500/30 px-2 py-0.5 rounded text-[10px] font-semibold">
            <XCircle className="w-3 h-3" />
            <span>FAILED</span>
          </span>
        );
      default:
        return (
          <span className="flex items-center space-x-1 text-cyan-400 bg-cyan-500/10 border border-cyan-500/30 px-2 py-0.5 rounded text-[10px] font-semibold">
            <Clock className="w-3 h-3" />
            <span>{status || "PLANNED"}</span>
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
        </div>
        <button
          onClick={loadTasks}
          disabled={loading}
          className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-all"
          title="Refresh tasks"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {/* Task Selector Bar */}
      <div className="px-4 py-2 bg-slate-950/20 border-b border-slate-800/60 flex items-center space-x-2 overflow-x-auto text-xs">
        <span className="text-slate-500 shrink-0 font-medium">Recent Tasks:</span>
        {tasks.map((t) => (
          <button
            key={t.id}
            onClick={() => selectTask(t.id)}
            className={`px-3 py-1 rounded-lg shrink-0 border transition-all text-[11px] ${
              activeTask?.id === t.id
                ? "bg-cyan-500/20 text-cyan-300 border-cyan-500/40 font-semibold"
                : "bg-slate-900 text-slate-400 border-slate-800 hover:text-slate-200"
            }`}
          >
            {t.intent?.goal ? t.intent.goal.slice(0, 24) + "..." : t.id.slice(0, 8)}
          </button>
        ))}
        {tasks.length === 0 && <span className="text-slate-600">No recent tasks found</span>}
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
                <span>Task ID: {activeTask.id.slice(0, 13)}...</span>
                <span>Path: <strong className="text-cyan-400">{activeTask.path || "SMART"}</strong></span>
                <span>Steps: {activeTask.steps?.length || 0}</span>
              </div>
            </div>

            {/* Steps Timeline (DAG Nodes) */}
            <div className="space-y-3">
              <h4 className="text-xs font-semibold text-slate-400 tracking-wide uppercase">Execution Steps</h4>
              {activeTask.steps?.map((step: any, index: number) => (
                <div
                  key={step.id || index}
                  className="bg-slate-900/90 border border-slate-800/80 rounded-xl p-3 space-y-2 relative"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <span className="w-5 h-5 rounded-full bg-slate-800 text-slate-400 text-[10px] font-bold flex items-center justify-center">
                        {index + 1}
                      </span>
                      <span className="font-semibold text-xs text-slate-200">{step.step_key}</span>
                      <span className="text-[10px] px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/30">
                        {step.capability}
                      </span>
                    </div>
                    {getStatusBadge(step.status)}
                  </div>

                  {/* Inputs & Outputs viewer */}
                  <div className="bg-slate-950/90 rounded-lg p-2 font-mono text-[10px] text-slate-400 space-y-1">
                    {step.inputs && Object.keys(step.inputs).length > 0 && (
                      <div>
                        <span className="text-slate-500">inputs: </span>
                        <span>{JSON.stringify(step.inputs).slice(0, 80)}...</span>
                      </div>
                    )}
                    {step.outputs && Object.keys(step.outputs).length > 0 && (
                      <div>
                        <span className="text-emerald-500">outputs: </span>
                        <span>{JSON.stringify(step.outputs).slice(0, 80)}...</span>
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
              ))}
            </div>
          </div>
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-slate-500 text-xs space-y-2">
            <Terminal className="w-8 h-8 text-slate-600" />
            <p>No task selected. Execute a command in chat to visualize its DAG.</p>
          </div>
        )}
      </div>
    </div>
  );
};

