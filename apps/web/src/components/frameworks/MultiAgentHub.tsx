"use client";

import React, { useState, useEffect } from "react";
import {
  fetchFrameworks,
  runFrameworkTask,
  FrameworkInfo,
  FrameworkTemplate,
  FrameworkRunResult,
} from "@/lib/api";
import {
  Users,
  Network,
  Bot,
  Play,
  CheckCircle2,
  Clock,
  Sparkles,
  Layers,
  ArrowRight,
  ShieldCheck,
  Cpu,
  MessageSquare,
  RefreshCw,
} from "lucide-react";

export function MultiAgentHub() {
  const [frameworks, setFrameworks] = useState<FrameworkInfo[]>([]);
  const [selectedFramework, setSelectedFramework] = useState<string>("crewai");
  const [selectedTemplate, setSelectedTemplate] = useState<string>("");
  const [taskPrompt, setTaskPrompt] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [runResult, setRunResult] = useState<FrameworkRunResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadFrameworks();
  }, []);

  async function loadFrameworks() {
    try {
      const data = await fetchFrameworks();
      setFrameworks(data);
      if (data.length > 0) {
        const fw = data[0];
        setSelectedFramework(fw.framework);
        if (fw.templates.length > 0) {
          setSelectedTemplate(fw.templates[0].id);
          setDefaultPromptForTemplate(fw.framework, fw.templates[0].id);
        }
      }
    } catch (err: any) {
      console.error("Failed to load frameworks:", err);
    }
  }

  function setDefaultPromptForTemplate(fw: string, tmplId: string) {
    if (fw === "crewai") {
      if (tmplId === "code_review") {
        setTaskPrompt("Perform an architectural code review and security audit of an asynchronous FastAPI microservice handling JWT authentication and Redis rate limiting.");
      } else if (tmplId === "content_strategy") {
        setTaskPrompt("Design a comprehensive content strategy and technical announcement for an autonomous AI operating system with voice synthesis.");
      } else {
        setTaskPrompt("Conduct an in-depth research investigation on autonomous multi-agent coordination architectures and deterministic policy guardrails.");
      }
    } else if (fw === "langgraph") {
      if (tmplId === "data_pipeline") {
        setTaskPrompt("Execute data ingestion and schema validation for user transaction logs with cyclic correction on malformed records.");
      } else if (tmplId === "support_triage") {
        setTaskPrompt("Triage and resolve a high-priority customer escalation regarding webhook delivery timeouts and token expiration.");
      } else {
        setTaskPrompt("Process and synthesize unstructured quarterly performance metrics through entity extraction and validation loops.");
      }
    } else if (fw === "autogen") {
      if (tmplId === "strategy_debate") {
        setTaskPrompt("Debate the trade-offs of Microservices vs Event-Driven Modular Monolith for a high-throughput AI agent platform.");
      } else {
        setTaskPrompt("Collaboratively design and verify a Python async worker queue with exponential backoff and idempotency keys.");
      }
    }
  }

  function handleFrameworkChange(fwName: string) {
    setSelectedFramework(fwName);
    const fw = frameworks.find((f) => f.framework === fwName);
    if (fw && fw.templates.length > 0) {
      setSelectedTemplate(fw.templates[0].id);
      setDefaultPromptForTemplate(fwName, fw.templates[0].id);
    }
  }

  function handleTemplateChange(tmplId: string) {
    setSelectedTemplate(tmplId);
    setDefaultPromptForTemplate(selectedFramework, tmplId);
  }

  async function handleExecute() {
    if (!taskPrompt.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await runFrameworkTask(selectedFramework, taskPrompt, selectedTemplate);
      setRunResult(res);
    } catch (err: any) {
      setError(err.message || "Execution failed");
    } finally {
      setLoading(false);
    }
  }

  const currentFw = frameworks.find((f) => f.framework === selectedFramework);
  const currentTemplate = currentFw?.templates.find((t) => t.id === selectedTemplate);

  return (
    <div className="flex flex-col h-full space-y-4 overflow-y-auto pr-1">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 border border-indigo-900/40 rounded-xl p-5 shadow-lg flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-2 rounded-lg bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
              <Users className="w-5 h-5" />
            </span>
            <h2 className="text-xl font-bold text-white tracking-wide">Multi-Agent Framework Hub</h2>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 font-semibold">
              Gemini 2.5 Flash Connected
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl">
            Command specialized autonomous squads powered by <strong>CrewAI</strong>, <strong>LangGraph</strong>, and <strong>Microsoft AutoGen</strong>. Governed deterministically by OmniBrain's Policy Engine.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-slate-800/80 px-3 py-1.5 rounded-lg border border-slate-700/60 text-xs">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span className="text-slate-300">Policy Engine: Active</span>
          </div>
          <div className="flex items-center gap-2 bg-slate-800/80 px-3 py-1.5 rounded-lg border border-slate-700/60 text-xs">
            <Cpu className="w-4 h-4 text-blue-400" />
            <span className="text-slate-300">₹0 LLM Cost</span>
          </div>
        </div>
      </div>

      {/* Framework Selector Tabs */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {[
          {
            id: "crewai",
            name: "CrewAI",
            tagline: "Collaborative Crews & Autonomous Roles",
            icon: Users,
            color: "text-purple-400",
            borderColor: "border-purple-500/40",
            bgColor: "bg-purple-500/10",
          },
          {
            id: "langgraph",
            name: "LangGraph / LangChain",
            tagline: "Cyclic State Graphs & Workflow Loops",
            icon: Network,
            color: "text-blue-400",
            borderColor: "border-blue-500/40",
            bgColor: "bg-blue-500/10",
          },
          {
            id: "autogen",
            name: "Microsoft AutoGen",
            tagline: "Conversational Debate & Pair-Programming",
            icon: Bot,
            color: "text-emerald-400",
            borderColor: "border-emerald-500/40",
            bgColor: "bg-emerald-500/10",
          },
        ].map((fw) => {
          const isSelected = selectedFramework === fw.id;
          const Icon = fw.icon;
          return (
            <button
              key={fw.id}
              onClick={() => handleFrameworkChange(fw.id)}
              className={`p-4 rounded-xl border text-left transition-all relative overflow-hidden ${
                isSelected
                  ? `bg-slate-900 ${fw.borderColor} shadow-lg shadow-indigo-950/40 ring-1 ring-indigo-500/30`
                  : "bg-slate-900/60 border-slate-800 hover:border-slate-700 hover:bg-slate-900/90"
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div className={`p-2 rounded-lg ${fw.bgColor} ${fw.color}`}>
                    <Icon className="w-5 h-5" />
                  </div>
                  <span className="font-bold text-sm text-white">{fw.name}</span>
                </div>
                {isSelected && (
                  <span className="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_8px_#34d399]" />
                )}
              </div>
              <p className="text-xs text-slate-400 mt-2">{fw.tagline}</p>
            </button>
          );
        })}
      </div>

      {/* Main Configuration & Execution Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 flex-1">
        {/* Left Column: Squad & Task Configuration */}
        <div className="lg:col-span-5 flex flex-col space-y-4">
          {/* Squad / Graph Template Picker */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-md space-y-3">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold text-slate-300 flex items-center gap-2">
                <Layers className="w-4 h-4 text-indigo-400" />
                Select Squad / Graph Architecture
              </label>
              <span className="text-[11px] text-slate-500">
                {currentFw?.templates.length || 0} Templates
              </span>
            </div>

            <div className="space-y-2">
              {currentFw?.templates.map((tmpl) => (
                <button
                  key={tmpl.id}
                  onClick={() => handleTemplateChange(tmpl.id)}
                  className={`w-full p-3 rounded-lg border text-left transition-all ${
                    selectedTemplate === tmpl.id
                      ? "bg-indigo-950/40 border-indigo-500/50 text-white"
                      : "bg-slate-950/40 border-slate-800/80 text-slate-400 hover:text-slate-200 hover:border-slate-700"
                  }`}
                >
                  <div className="font-medium text-xs flex items-center justify-between">
                    <span>{tmpl.name}</span>
                    {selectedTemplate === tmpl.id && (
                      <CheckCircle2 className="w-3.5 h-3.5 text-indigo-400" />
                    )}
                  </div>
                  <p className="text-[11px] text-slate-400 mt-1 line-clamp-2">{tmpl.description}</p>
                  
                  {/* Agents or Nodes preview */}
                  {tmpl.agents && (
                    <div className="flex flex-wrap gap-1.5 mt-2">
                      {tmpl.agents.map((a: any) => (
                        <span key={a.name} className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700/50">
                          {a.role}
                        </span>
                      ))}
                    </div>
                  )}
                  {tmpl.nodes && (
                    <div className="flex items-center gap-1 mt-2 text-[10px] text-slate-400">
                      {tmpl.nodes.map((n: string, i: number) => (
                        <React.Fragment key={n}>
                          <span className="px-1.5 py-0.5 rounded bg-slate-800 text-blue-300 font-mono">
                            {n}
                          </span>
                          {i < tmpl.nodes!.length - 1 && <ArrowRight className="w-2.5 h-2.5 text-slate-600" />}
                        </React.Fragment>
                      ))}
                    </div>
                  )}
                </button>
              ))}
            </div>
          </div>

          {/* Task Instruction Input */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-md space-y-3 flex-1 flex flex-col">
            <label className="text-xs font-semibold text-slate-300 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-amber-400" />
              Task Objective / Prompt
            </label>
            <textarea
              value={taskPrompt}
              onChange={(e) => setTaskPrompt(e.target.value)}
              rows={4}
              placeholder="Enter instructions for the agent squad..."
              className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-xs text-slate-100 placeholder-slate-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 resize-none flex-1"
            />

            {error && (
              <div className="p-2.5 bg-rose-500/10 border border-rose-500/30 rounded-lg text-rose-400 text-xs">
                {error}
              </div>
            )}

            <button
              onClick={handleExecute}
              disabled={loading || !taskPrompt.trim()}
              className="w-full py-2.5 px-4 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-xs font-semibold rounded-lg shadow-md flex items-center justify-center gap-2 transition-all"
            >
              {loading ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Orchestrating Agents...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-white" />
                  Deploy Agent Squad
                </>
              )}
            </button>
          </div>
        </div>

        {/* Right Column: Live Agent Dialogue & Synthesis */}
        <div className="lg:col-span-7 flex flex-col space-y-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-md flex-1 flex flex-col min-h-[480px]">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <MessageSquare className="w-4 h-4 text-indigo-400" />
                <h3 className="text-xs font-bold text-white uppercase tracking-wider">
                  Agent Dialogue & Collaboration Stream
                </h3>
              </div>
              {runResult && (
                <div className="flex items-center gap-3 text-xs">
                  <span className="flex items-center gap-1 text-slate-400">
                    <Clock className="w-3.5 h-3.5" />
                    {runResult.execution_time_ms}ms
                  </span>
                  <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 font-semibold text-[11px]">
                    {runResult.status}
                  </span>
                </div>
              )}
            </div>

            {/* Dialogue View Area */}
            <div className="flex-1 overflow-y-auto py-3 space-y-3">
              {!runResult && !loading && (
                <div className="h-full flex flex-col items-center justify-center text-center p-8 text-slate-500">
                  <Users className="w-12 h-12 mb-3 text-slate-700" />
                  <p className="text-sm font-medium text-slate-400">No squad currently deployed</p>
                  <p className="text-xs text-slate-600 max-w-sm mt-1">
                    Select a framework architecture on the left and click <strong>Deploy Agent Squad</strong> to watch agents interact and resolve complex tasks.
                  </p>
                </div>
              )}

              {loading && (
                <div className="h-full flex flex-col items-center justify-center text-center p-8 space-y-3">
                  <div className="relative">
                    <div className="w-12 h-12 rounded-full border-2 border-indigo-500/20 border-t-indigo-500 animate-spin" />
                    <Bot className="w-6 h-6 text-indigo-400 absolute inset-0 m-auto" />
                  </div>
                  <p className="text-sm text-slate-300 font-medium">Agents are conversing and collaborating...</p>
                  <p className="text-xs text-slate-500">Evaluating hypotheses, critiquing drafts, and reaching consensus.</p>
                </div>
              )}

              {runResult && (
                <>
                  {runResult.agent_dialogue.map((msg, idx) => {
                    const isCritic = msg.role.toLowerCase().includes("critic") || msg.name.includes("critic");
                    const isNode = msg.role.toLowerCase().includes("node") || msg.role.toLowerCase().includes("edge");
                    const isSynthesizer = msg.role.toLowerCase().includes("synthesis") || msg.role.toLowerCase().includes("arbiter");

                    return (
                      <div
                        key={idx}
                        className="bg-slate-950/70 border border-slate-800/80 rounded-lg p-3.5 text-xs transition-all hover:border-slate-700"
                      >
                        <div className="flex items-center justify-between mb-1.5">
                          <div className="flex items-center gap-2">
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                isCritic
                                  ? "bg-rose-500/15 text-rose-300 border border-rose-500/30"
                                  : isNode
                                  ? "bg-blue-500/15 text-blue-300 border border-blue-500/30"
                                  : isSynthesizer
                                  ? "bg-purple-500/15 text-purple-300 border border-purple-500/30"
                                  : "bg-emerald-500/15 text-emerald-300 border border-emerald-500/30"
                              }`}
                            >
                              {msg.role}
                            </span>
                            <span className="font-semibold text-slate-300">{msg.name}</span>
                          </div>
                          <span className="text-[10px] text-slate-500 font-mono">
                            {new Date(msg.timestamp).toLocaleTimeString()}
                          </span>
                        </div>
                        <p className="text-slate-300 whitespace-pre-wrap leading-relaxed">
                          {msg.content}
                        </p>
                      </div>
                    );
                  })}

                  {/* Final Output Synthesis Card */}
                  <div className="mt-4 bg-gradient-to-br from-indigo-950/40 via-slate-950 to-purple-950/40 border border-indigo-500/40 rounded-xl p-4 shadow-lg">
                    <div className="flex items-center gap-2 mb-2 text-indigo-400 font-bold text-xs">
                      <Sparkles className="w-4 h-4" />
                      Consolidated Final Synthesis
                    </div>
                    <div className="text-xs text-slate-200 whitespace-pre-wrap leading-relaxed font-sans">
                      {runResult.final_output}
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

