"use client";

import React, { useEffect, useState } from "react";
import { Brain, Volume2, VolumeX, Shield, Activity, Radio, Bell, Users, Mic } from "lucide-react";
import { fetchHealthCenter, fetchNotifications } from "@/lib/api";
import NotificationCenter from "./notifications/NotificationCenter";
import { VoiceCloneStudio } from "./voice/VoiceCloneStudio";

interface NavbarProps {
  activeTab: "chat" | "approvals" | "integrations" | "workflows" | "webhooks" | "settings" | "frameworks";
  setActiveTab: (tab: "chat" | "approvals" | "integrations" | "workflows" | "webhooks" | "settings" | "frameworks") => void;
  isVoiceMuted: boolean;
  setIsVoiceMuted: (muted: boolean) => void;
  selectedVoice: string;
  setSelectedVoice: (voice: string) => void;
  pendingApprovalsCount: number;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  isVoiceMuted,
  setIsVoiceMuted,
  selectedVoice,
  setSelectedVoice,
  pendingApprovalsCount,
}) => {
  const [healthStatus, setHealthStatus] = useState<string>("ONLINE");
  const [isNotificationsOpen, setIsNotificationsOpen] = useState<boolean>(false);
  const [unreadNotifsCount, setUnreadNotifsCount] = useState<number>(0);
  const [autonomyLevel, setAutonomyLevel] = useState<number>(2);
  const [isVoiceStudioOpen, setIsVoiceStudioOpen] = useState<boolean>(false);

  useEffect(() => {
    fetchHealthCenter().then((data) => {
      if (data && data.status) {
        setHealthStatus(data.status.toUpperCase());
      }
    });
    fetchNotifications().then((data) => {
      setUnreadNotifsCount(data.unread_count || 0);
    }).catch(() => {});
  }, []);

  return (
    <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur-md sticky top-0 z-50 px-6 py-3.5 flex items-center justify-between">
      {/* Brand & Persona */}
      <div className="flex items-center space-x-4">
        <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400 shadow-lg shadow-cyan-500/10">
          <Brain className="w-5 h-5" />
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <span className="font-bold text-base tracking-wide text-white">OmniBrain</span>
            <span className="text-[10px] font-semibold bg-cyan-500/20 text-cyan-300 px-2 py-0.5 rounded border border-cyan-500/30 tracking-wider">
              S.A.R.A.
            </span>
          </div>
          <p className="text-xs text-slate-400">Personal Autonomous AI Operating System</p>
        </div>
      </div>

      {/* Navigation Tabs */}
      <nav className="flex items-center space-x-1 bg-slate-900/90 p-1 rounded-xl border border-slate-800">
        <button
          onClick={() => setActiveTab("chat")}
          className={`px-4 py-1.5 rounded-lg text-xs font-medium transition-all ${
            activeTab === "chat"
              ? "bg-cyan-500 text-slate-950 font-semibold shadow-sm"
              : "text-slate-400 hover:text-white"
          }`}
        >
          Chat & DAG Execution
        </button>
        <button
          onClick={() => setActiveTab("approvals")}
          className={`relative px-4 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center space-x-1.5 ${
            activeTab === "approvals"
              ? "bg-cyan-500 text-slate-950 font-semibold shadow-sm"
              : "text-slate-400 hover:text-white"
          }`}
        >
          <span>Approvals Inbox</span>
          {pendingApprovalsCount > 0 && (
            <span className="w-4 h-4 rounded-full bg-amber-500 text-slate-950 text-[10px] font-bold flex items-center justify-center">
              {pendingApprovalsCount}
            </span>
          )}
        </button>
        <button
          onClick={() => setActiveTab("integrations")}
          className={`px-4 py-1.5 rounded-lg text-xs font-medium transition-all ${
            activeTab === "integrations"
              ? "bg-cyan-500 text-slate-950 font-semibold shadow-sm"
              : "text-slate-400 hover:text-white"
          }`}
        >
          Integrations Hub
        </button>
        <button
          onClick={() => setActiveTab("workflows")}
          className={`px-4 py-1.5 rounded-lg text-xs font-medium transition-all ${
            activeTab === "workflows"
              ? "bg-cyan-500 text-slate-950 font-semibold shadow-sm"
              : "text-slate-400 hover:text-white"
          }`}
        >
          Workflows
        </button>
        <button
          onClick={() => setActiveTab("webhooks")}
          className={`px-4 py-1.5 rounded-lg text-xs font-medium transition-all ${
            activeTab === "webhooks"
              ? "bg-cyan-500 text-slate-950 font-semibold shadow-sm"
              : "text-slate-400 hover:text-white"
          }`}
        >
          Webhooks & Mobile
        </button>
        <button
          onClick={() => setActiveTab("frameworks")}
          className={`px-4 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center space-x-1.5 ${
            activeTab === "frameworks"
              ? "bg-cyan-500 text-slate-950 font-semibold shadow-sm"
              : "text-slate-400 hover:text-white"
          }`}
        >
          <Users className="w-3.5 h-3.5" />
          <span>Multi-Agent Hub</span>
        </button>
        <button
          onClick={() => setActiveTab("settings")}
          className={`px-4 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center space-x-1 ${
            activeTab === "settings"
              ? "bg-cyan-500 text-slate-950 font-semibold shadow-sm"
              : "text-slate-400 hover:text-white"
          }`}
        >
          <Shield className="w-3.5 h-3.5" />
          <span>Safety & Autonomy</span>
        </button>
      </nav>

      {/* Controls & Telemetry */}
      <div className="flex items-center space-x-3">
        {/* Voice Mute Toggle */}
        <button
          onClick={() => setIsVoiceMuted(!isVoiceMuted)}
          className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
            isVoiceMuted
              ? "border-rose-500/40 bg-rose-500/10 text-rose-300 hover:bg-rose-500/20"
              : "border-emerald-500/40 bg-emerald-500/10 text-emerald-300 hover:bg-emerald-500/20"
          }`}
        >
          {isVoiceMuted ? <VolumeX className="w-3.5 h-3.5" /> : <Volume2 className="w-3.5 h-3.5" />}
          <span>{isVoiceMuted ? "Voice: OFF" : "Voice: ON"}</span>
        </button>

        {/* Voice Selector */}
        <div className="flex items-center space-x-1.5 bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-lg text-xs">
          <Radio className="w-3 h-3 text-cyan-400" />
          <select
            value={selectedVoice}
            onChange={(e) => setSelectedVoice(e.target.value)}
            className="bg-transparent text-slate-200 outline-none text-xs cursor-pointer"
          >
            <option value="auto" className="bg-slate-900">Auto (Hindi & English)</option>
            <option value="custom_clone" className="bg-slate-900">🎙️ My Cloned Voice</option>
            <option value="hi-IN-SwaraNeural" className="bg-slate-900">Swara (Hindi Lady)</option>
            <option value="en-US-JennyNeural" className="bg-slate-900">Jenny (English Lady)</option>
          </select>
        </div>

        {/* Voice Clone Studio Button */}
        <button
          onClick={() => setIsVoiceStudioOpen(true)}
          className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border border-purple-500/30 bg-purple-500/10 text-purple-300 hover:bg-purple-500/20 transition-all cursor-pointer shadow-sm"
          title="Open Voice Clone Studio"
        >
          <Mic className="w-3.5 h-3.5" />
          <span>Voice Studio</span>
        </button>

        {/* Emergency STOP Button */}
        <button
          onClick={async () => {
            if (confirm("EMERGENCY STOP: Halt all autonomous actions?")) {
              try {
                const token = localStorage.getItem("omnibrain_token");
                await fetch("http://localhost:8000/v1/safety/kill-switch", {
                  method: "POST",
                  headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
                  body: JSON.stringify({ active: true, reason: "Manual UI trigger" })
                });
                alert("System Halted.");
                window.location.reload();
              } catch (e) {
                console.error(e);
              }
            }
          }}
          className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-bold border border-red-500/50 bg-red-500/20 text-red-100 hover:bg-red-500/40 transition-all shadow-md animate-pulse cursor-pointer"
          title="EMERGENCY STOP (Halt all tasks)"
        >
          <div className="w-2 h-2 rounded-full bg-red-400 mr-1 shadow-[0_0_8px_rgba(248,113,113,0.8)]"></div>
          <span>STOP</span>
        </button>

        {/* Proactive Notifications Bell */}
        <button
          onClick={() => setIsNotificationsOpen(!isNotificationsOpen)}
          className={`relative p-2 rounded-lg border transition-all ${
            isNotificationsOpen
              ? "bg-indigo-600/30 border-indigo-500 text-indigo-300"
              : "bg-slate-900 border-slate-800 text-slate-300 hover:text-white hover:bg-slate-800"
          }`}
          title="Proactive Notifications"
        >
          <Bell className="w-4 h-4" />
          {unreadNotifsCount > 0 && (
            <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-indigo-500 text-white text-[9px] font-bold flex items-center justify-center animate-pulse shadow-md shadow-indigo-500/50">
              {unreadNotifsCount > 9 ? "9+" : unreadNotifsCount}
            </span>
          )}
        </button>

        {/* Interactive Autonomy Level Badge */}
        <button
          onClick={() => setActiveTab("settings")}
          className="hidden md:flex items-center space-x-1.5 bg-slate-900 hover:bg-slate-800 border border-slate-800 px-3 py-1.5 rounded-lg text-xs text-slate-300 transition-all cursor-pointer"
          title="Manage Autonomy Level & Emergency Stop"
        >
          <Shield className="w-3.5 h-3.5 text-indigo-400" />
          <span>Level 2: Guarded</span>
        </button>

        {/* System Health */}
        <div className="flex items-center space-x-1.5 bg-slate-900/60 border border-slate-800 px-3 py-1.5 rounded-lg text-xs text-emerald-400">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span>{healthStatus}</span>
        </div>
      </div>

      {/* Notification Center Slide-over Drawer */}
      <NotificationCenter
        isOpen={isNotificationsOpen}
        onClose={() => setIsNotificationsOpen(false)}
        onUnreadChange={(count) => setUnreadNotifsCount(count)}
      />

      {/* Voice Clone Studio Modal */}
      <VoiceCloneStudio
        isOpen={isVoiceStudioOpen}
        onClose={() => setIsVoiceStudioOpen(false)}
        onVoiceActivated={(voice) => setSelectedVoice(voice)}
      />
    </header>
  );
};

