"use client";

import React, { useEffect, useState } from "react";
import {
  Workflow as WorkflowIcon,
  Play,
  RotateCw,
  Clock,
  CheckCircle2,
  XCircle,
  Loader2,
  Calendar,
  Github,
  MessageSquare,
  Globe,
  Mail,
  ChevronRight,
  Layers,
  ArrowRight,
  Sparkles,
} from "lucide-react";
import {
  fetchWorkflows,
  runWorkflow,
  fetchWorkflowRuns,
  Workflow,
  WorkflowRun,
} from "@/lib/api";

export const WorkflowsDashboard: React.FC = () => {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [runningId, setRunningId] = useState<string | null>(null);
  const [selectedWorkflow, setSelectedWorkflow] = useState<Workflow | null>(null);
  const [runs, setRuns] = useState<WorkflowRun[]>([]);
  const [loadingRuns, setLoadingRuns] = useState(false);
  const [notificationMsg, setNotificationMsg] = useState<string | null>(null);

  const loadWorkflows = async () => {
    setIsLoading(true);
    try {
      const data = await fetchWorkflows();
      setWorkflows(data.workflows || []);
    } catch (err) {
      console.error("Failed to load workflows:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadWorkflows();
  }, []);

  const handleRunWorkflow = async (wf: Workflow) => {
    setRunningId(wf.id);
    setNotificationMsg(null);
    try {
      const run = await runWorkflow(wf.id);
      setNotificationMsg(`Workflow "${wf.name}" completed successfully with status: ${run.status}`);
      if (selectedWorkflow?.id === wf.id) {
        loadRuns(wf.id);
      }
    } catch (err: any) {
      setNotificationMsg(`Execution failed: ${err.message || "Unknown error"}`);
    } finally {
      setRunningId(null);
    }
  };

  const loadRuns = async (workflowId: string) => {
    setLoadingRuns(true);
    try {
      const history = await fetchWorkflowRuns(workflowId);
      setRuns(history);
    } catch (err) {
      console.error("Failed to load runs:", err);
    } finally {
      setLoadingRuns(false);
    }
  };

  const openRunsDrawer = (wf: Workflow) => {
    setSelectedWorkflow(wf);
    loadRuns(wf.id);
  };

  const getConnectorIcon = (connector: string) => {
    switch (connector.toLowerCase()) {
      case "calendar":
      case "gcal":
        return <Calendar className="w-3.5 h-3.5 text-amber-400" />;
      case "github":
        return <Github className="w-3.5 h-3.5 text-purple-400" />;
      case "slack":
        return <MessageSquare className="w-3.5 h-3.5 text-emerald-400" />;
      case "browser":
        return <Globe className="w-3.5 h-3.5 text-cyan-400" />;
      case "gmail":
      case "mail":
        return <Mail className="w-3.5 h-3.5 text-rose-400" />;
      default:
        return <Layers className="w-3.5 h-3.5 text-slate-400" />;
    }
  };

  return (
    <div className="h-full flex flex-col space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between bg-slate-900/60 border border-slate-800/80 backdrop-blur-md rounded-2xl p-4 px-6 shadow-lg">
        <div className="flex items-center space-x-3.5">
          <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
            <WorkflowIcon className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-base font-semibold text-white tracking-wide flex items-center space-x-2">
              <span>Multi-Step Automation Workflows</span>
              <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                Phase 6 Active
              </span>
            </h1>
            <p className="text-xs text-slate-400">
              Deterministic DAG workflows coordinating cross-platform tool connectors autonomously.
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={loadWorkflows}
            disabled={isLoading}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl text-xs font-medium text-slate-300 bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700/60 transition-all cursor-pointer"
          >
            <RotateCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin text-cyan-400" : ""}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Execution Alert Banner */}
      {notificationMsg && (
        <div className="p-3 px-4 rounded-xl bg-cyan-950/40 border border-cyan-500/30 text-cyan-200 text-xs flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Sparkles className="w-4 h-4 text-cyan-400" />
            <span>{notificationMsg}</span>
          </div>
          <button
            onClick={() => setNotificationMsg(null)}
            className="text-slate-400 hover:text-white text-xs"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Main Grid: Workflows List & Run History Drawer */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-4 overflow-hidden">
        {/* Workflows Column */}
        <div className={`${selectedWorkflow ? "lg:col-span-7" : "lg:col-span-12"} overflow-y-auto space-y-3.5 pr-1`}>
          {isLoading ? (
            <div className="flex flex-col items-center justify-center py-20 space-y-3">
              <Loader2 className="w-7 h-7 text-cyan-400 animate-spin" />
              <p className="text-xs text-slate-400">Loading automated workflows...</p>
            </div>
          ) : workflows.length === 0 ? (
            <div className="text-center py-16 bg-slate-900/30 rounded-2xl border border-slate-800">
              <WorkflowIcon className="w-8 h-8 text-slate-600 mx-auto mb-2" />
              <p className="text-sm font-medium text-slate-300">No workflows found</p>
              <p className="text-xs text-slate-500 mt-1">Default templates will be seeded automatically on refresh.</p>
            </div>
          ) : (
            workflows.map((wf) => {
              const isRunning = runningId === wf.id;
              const isSelected = selectedWorkflow?.id === wf.id;
              const steps = wf.definition?.steps || [];

              return (
                <div
                  key={wf.id}
                  className={`p-5 rounded-2xl border transition-all ${
                    isSelected
                      ? "bg-slate-900/90 border-cyan-500/50 shadow-cyan-950/30 shadow-lg"
                      : "bg-slate-900/40 border-slate-800 hover:border-slate-700 hover:bg-slate-900/60"
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="space-y-1">
                      <div className="flex items-center space-x-2.5">
                        <h2 className="text-sm font-semibold text-white">{wf.name}</h2>
                        <span
                          className={`text-[10px] px-2 py-0.5 rounded font-mono font-medium ${
                            wf.trigger_type === "cron"
                              ? "bg-amber-500/10 text-amber-300 border border-amber-500/30"
                              : "bg-blue-500/10 text-blue-300 border border-blue-500/30"
                          }`}
                        >
                          {wf.trigger_type === "cron" ? `CRON: ${wf.cron_expression || "Scheduled"}` : "MANUAL TRIGGER"}
                        </span>
                      </div>
                      <p className="text-xs text-slate-400 leading-relaxed">{wf.description}</p>
                    </div>

                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => openRunsDrawer(wf)}
                        className={`px-3 py-1.5 rounded-xl text-xs font-medium border transition-all ${
                          isSelected
                            ? "bg-cyan-500/20 text-cyan-300 border-cyan-500/40"
                            : "bg-slate-800/80 text-slate-300 border-slate-700 hover:bg-slate-700"
                        }`}
                      >
                        History
                      </button>

                      <button
                        onClick={() => handleRunWorkflow(wf)}
                        disabled={isRunning}
                        className="flex items-center space-x-1.5 px-3.5 py-1.5 rounded-xl text-xs font-semibold bg-gradient-to-r from-cyan-500 to-blue-600 text-slate-950 hover:from-cyan-400 hover:to-blue-500 disabled:opacity-50 transition-all shadow-md shadow-cyan-500/20"
                      >
                        {isRunning ? (
                          <>
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                            <span>Running...</span>
                          </>
                        ) : (
                          <>
                            <Play className="w-3.5 h-3.5 fill-current" />
                            <span>Run Now</span>
                          </>
                        )}
                      </button>
                    </div>
                  </div>

                  {/* Step pipeline visualization */}
                  <div className="mt-4 pt-3.5 border-t border-slate-800/60">
                    <p className="text-[11px] font-medium text-slate-400 mb-2.5 flex items-center space-x-1.5">
                      <Layers className="w-3.5 h-3.5 text-cyan-400" />
                      <span>Pipeline Sequence ({steps.length} Steps)</span>
                    </p>
                    <div className="flex flex-wrap items-center gap-2">
                      {steps.map((step, idx) => (
                        <React.Fragment key={step.id}>
                          <div className="flex items-center space-x-1.5 bg-slate-800/80 border border-slate-700/70 rounded-lg px-2.5 py-1 text-xs">
                            {getConnectorIcon(step.connector)}
                            <span className="text-slate-200 font-medium">{step.name}</span>
                          </div>
                          {idx < steps.length - 1 && (
                            <ArrowRight className="w-3.5 h-3.5 text-slate-600" />
                          )}
                        </React.Fragment>
                      ))}
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Runs History Drawer / Column */}
        {selectedWorkflow && (
          <div className="lg:col-span-5 bg-slate-900/80 border border-slate-800 rounded-2xl p-5 flex flex-col h-full overflow-hidden shadow-xl">
            <div className="flex items-center justify-between pb-3.5 border-b border-slate-800">
              <div>
                <h3 className="text-sm font-semibold text-white">Execution History</h3>
                <p className="text-xs text-slate-400 truncate max-w-[280px]">{selectedWorkflow.name}</p>
              </div>
              <button
                onClick={() => setSelectedWorkflow(null)}
                className="text-slate-400 hover:text-white text-xs px-2 py-1 rounded bg-slate-800 border border-slate-700"
              >
                Close
              </button>
            </div>

            <div className="flex-1 overflow-y-auto space-y-3 pt-3 pr-1">
              {loadingRuns ? (
                <div className="py-12 text-center">
                  <Loader2 className="w-6 h-6 text-cyan-400 animate-spin mx-auto mb-2" />
                  <p className="text-xs text-slate-400">Loading run history...</p>
                </div>
              ) : runs.length === 0 ? (
                <div className="text-center py-12 text-slate-500 text-xs">
                  No previous runs recorded. Click "Run Now" to trigger this workflow.
                </div>
              ) : (
                runs.map((run) => {
                  const stepLogs = run.result?.step_logs || [];
                  const isSuccess = run.status === "COMPLETED";

                  return (
                    <div
                      key={run.id}
                      className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2.5 text-xs"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          {isSuccess ? (
                            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                          ) : run.status === "RUNNING" ? (
                            <Loader2 className="w-4 h-4 text-cyan-400 animate-spin" />
                          ) : (
                            <XCircle className="w-4 h-4 text-rose-400" />
                          )}
                          <span
                            className={`font-semibold uppercase tracking-wider text-[11px] ${
                              isSuccess
                                ? "text-emerald-400"
                                : run.status === "RUNNING"
                                ? "text-cyan-400"
                                : "text-rose-400"
                            }`}
                          >
                            {run.status}
                          </span>
                        </div>

                        <div className="flex items-center space-x-1 text-slate-400 text-[11px]">
                          <Clock className="w-3 h-3" />
                          <span>{new Date(run.started_at).toLocaleTimeString()}</span>
                        </div>
                      </div>

                      {/* Step Execution Logs */}
                      {stepLogs.length > 0 && (
                        <div className="space-y-1.5 pt-1">
                          {stepLogs.map((log) => (
                            <div
                              key={log.step_id}
                              className="flex items-center justify-between bg-slate-900/90 px-2.5 py-1.5 rounded-lg border border-slate-800/80 text-[11px]"
                            >
                              <div className="flex items-center space-x-1.5">
                                <span
                                  className={`w-1.5 h-1.5 rounded-full ${
                                    log.status === "COMPLETED"
                                      ? "bg-emerald-400"
                                      : log.status === "FAILED"
                                      ? "bg-rose-400"
                                      : "bg-cyan-400"
                                  }`}
                                />
                                <span className="text-slate-300 font-medium">{log.step_name}</span>
                              </div>
                              <span className="font-mono text-slate-500 text-[10px]">{log.action}</span>
                            </div>
                          ))}
                        </div>
                      )}

                      {run.error && (
                        <div className="p-2 rounded bg-rose-950/40 border border-rose-500/30 text-rose-300 text-[11px]">
                          Error: {run.error.error || "Execution failed"}
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
export default WorkflowsDashboard;

