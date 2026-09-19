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

export default function Home() {
  const [activeTab, setActiveTab] = useState<"chat" | "approvals" | "integrations" | "workflows" | "webhooks" | "settings" | "frameworks">("chat");
  const [isVoiceMuted, setIsVoiceMuted] = useState(false);
  const [selectedVoice, setSelectedVoice] = useState("auto");
  const [selectedTaskId, setSelectedTaskId] = useState<string | undefined>();
  const [pendingApprovalsCount, setPendingApprovalsCount] = useState(0);

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-slate-950">
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

      <main className="flex-1 p-5 overflow-hidden">
        {activeTab === "chat" && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 h-full min-h-0">
            <div className="lg:col-span-7 h-full min-h-0">
              <ChatPanel
                isVoiceMuted={isVoiceMuted}
                selectedVoice={selectedVoice}
                onTaskCreated={(id) => setSelectedTaskId(id)}
              />
            </div>
            <div className="lg:col-span-5 h-full min-h-0">
              <DAGVisualizer selectedTaskId={selectedTaskId} />
            </div>
          </div>
        )}

        {activeTab === "approvals" && (
          <div className="max-w-5xl mx-auto h-full">
            <ApprovalsInbox onCountChange={(count) => setPendingApprovalsCount(count)} />
          </div>
        )}

        {activeTab === "integrations" && (
          <div className="max-w-5xl mx-auto h-full">
            <IntegrationsHub />
          </div>
        )}

        {activeTab === "workflows" && (
          <div className="max-w-6xl mx-auto h-full">
            <WorkflowsDashboard />
          </div>
        )}

        {activeTab === "webhooks" && (
          <div className="max-w-6xl mx-auto h-full">
            <WebhooksHub />
          </div>
        )}

        {activeTab === "frameworks" && (
          <div className="max-w-6xl mx-auto h-full">
            <MultiAgentHub />
          </div>
        )}

        {activeTab === "settings" && (
          <div className="max-w-6xl mx-auto h-full">
            <AutonomySettingsHub />
          </div>
        )}
      </main>
    </div>
  );
}

