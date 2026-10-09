"use client";

import React, { useState } from "react";
import { Navbar } from "@/components/Navbar";
import { ChatPanel } from "@/components/chat/ChatPanel";
import { DAGVisualizer } from "@/components/dag/DAGVisualizer";
import { ApprovalsInbox } from "@/components/approvals/ApprovalsInbox";
import { IntegrationsHub } from "@/components/connectors/IntegrationsHub";
import { WorkflowsDashboard } from "@/components/workflows/WorkflowsDashboard";
import { WebhooksHub } from "@/components/events/WebhooksHub";
import { EmergencyBanner } from "@/components/safety/EmergencyBanner";
import { AutonomySettingsHub } from "@/components/safety/AutonomySettingsHub";
import { MultiAgentHub } from "@/components/frameworks/MultiAgentHub";
import { MessageSquare, GitCommit, ArrowRight } from "lucide-react";

export default function Home() {
  const [activeTab, setActiveTab] = useState<
    "chat" | "approvals" | "integrations" | "workflows" | "webhooks" | "settings" | "frameworks"
  >("chat");
  const [isVoiceMuted, setIsVoiceMuted] = useState(false);
  const [selectedVoice, setSelectedVoice] = useState("auto");
  const [selectedTaskId, setSelectedTaskId] = useState<string | undefined>();
  const [pendingApprovalsCount, setPendingApprovalsCount] = useState(0);

  const [mobileSubView, setMobileSubView] = useState<"chat" | "dag">("chat");
  const [lastCreatedTaskId, setLastCreatedTaskId] = useState<string | null>(null);

  const handleTaskCreated = (id: string) => {
    setSelectedTaskId(id);
    setLastCreatedTaskId(id);
  };

  return (
    <div className="flex flex-col h-screen w-full max-w-full overflow-hidden bg-slate-950">
      <EmergencyBanner />
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        isVoiceMuted={isVoiceMuted}
        setIsVoiceMuted={setIsVoiceMuted}
        selectedVoice={selectedVoice}
        setSelectedVoice={setSelectedVoice}
        pendingApprovalsCount={pendingApprovalsCount}
      />

      <main className="flex-1 p-2 sm:p-4 lg:p-5 overflow-hidden min-h-0 min-w-0">
        {activeTab === "chat" && (
          <div className="h-full flex flex-col min-h-0 min-w-0">
            {/* Tablet/Mobile Segmented Control (< 1024px) */}
            <div className="flex lg:hidden items-center justify-between gap-2 mb-2 shrink-0">
              <div className="flex items-center bg-slate-900/90 p-1 rounded-xl border border-slate-800 flex-1">
                <button
                  onClick={() => setMobileSubView("chat")}
                  className={`flex-1 py-1.5 px-3 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition-all min-h-[36px] cursor-pointer ${
                    mobileSubView === "chat"
                      ? "bg-cyan-500 text-slate-950 shadow-md font-bold"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  <MessageSquare className="w-3.5 h-3.5" />
                  <span>Live Dialogue</span>
                </button>
                <button
                  onClick={() => setMobileSubView("dag")}
                  className={`flex-1 py-1.5 px-3 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition-all min-h-[36px] cursor-pointer relative ${
                    mobileSubView === "dag"
                      ? "bg-cyan-500 text-slate-950 shadow-md font-bold"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  <GitCommit className="w-3.5 h-3.5" />
                  <span>DAG Pipeline</span>
                  {lastCreatedTaskId && (
                    <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse ml-1" />
                  )}
                </button>
              </div>

              {lastCreatedTaskId && mobileSubView === "chat" && (
                <button
                  onClick={() => {
                    setMobileSubView("dag");
                    setLastCreatedTaskId(null);
                  }}
                  className="px-2.5 py-1.5 bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/40 rounded-xl text-xs font-medium flex items-center gap-1 shrink-0 animate-pulse min-h-[36px] cursor-pointer"
                >
                  <span>View DAG</span>
                  <ArrowRight className="w-3 h-3" />
                </button>
              )}
            </div>

            {/* Desktop: Side-by-Side (>= 1024px) */}
            <div className="hidden lg:grid lg:grid-cols-12 gap-5 h-full min-h-0 min-w-0">
              <div className="lg:col-span-7 h-full min-h-0 min-w-0">
                <ChatPanel
                  isVoiceMuted={isVoiceMuted}
                  selectedVoice={selectedVoice}
                  onTaskCreated={handleTaskCreated}
                />
              </div>
              <div className="lg:col-span-5 h-full min-h-0 min-w-0">
                <DAGVisualizer selectedTaskId={selectedTaskId} />
              </div>
            </div>

            {/* Tablet/Mobile View (< 1024px) */}
            <div className="flex-1 lg:hidden min-h-0 min-w-0">
              {mobileSubView === "chat" ? (
                <div className="h-full min-h-0 min-w-0">
                  <ChatPanel
                    isVoiceMuted={isVoiceMuted}
                    selectedVoice={selectedVoice}
                    onTaskCreated={handleTaskCreated}
                  />
                </div>
              ) : (
                <div className="h-full min-h-0 min-w-0">
                  <DAGVisualizer selectedTaskId={selectedTaskId} />
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === "approvals" && (
          <div className="max-w-5xl mx-auto h-full min-h-0">
            <ApprovalsInbox onCountChange={(count) => setPendingApprovalsCount(count)} />
          </div>
        )}

        {activeTab === "integrations" && (
          <div className="max-w-5xl mx-auto h-full min-h-0">
            <IntegrationsHub />
          </div>
        )}

        {activeTab === "workflows" && (
          <div className="max-w-6xl mx-auto h-full min-h-0">
            <WorkflowsDashboard />
          </div>
        )}

        {activeTab === "webhooks" && (
          <div className="max-w-6xl mx-auto h-full min-h-0">
            <WebhooksHub />
          </div>
        )}

        {activeTab === "frameworks" && (
          <div className="max-w-6xl mx-auto h-full min-h-0">
            <MultiAgentHub />
          </div>
        )}

        {activeTab === "settings" && (
          <div className="max-w-6xl mx-auto h-full min-h-0">
            <AutonomySettingsHub />
          </div>
        )}
      </main>
    </div>
  );
}
