"use client";

import React, { useEffect, useState } from "react";
import {
  Smartphone,
  Webhook,
  Activity,
  Copy,
  Check,
  RotateCw,
  Terminal,
  Zap,
  Radio,
  Clock,
  ShieldCheck,
  Send,
  Loader2,
  Sparkles,
} from "lucide-react";
import {
  fetchRecentEvents,
  fetchWebhooksInfo,
  triggerMobileSimulation,
  WebhookEventItem,
  API_BASE,
} from "@/lib/api";

export const WebhooksHub: React.FC = () => {
  const [events, setEvents] = useState<WebhookEventItem[]>([]);
  const [loadingEvents, setLoadingEvents] = useState(false);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [simulating, setSimulating] = useState(false);
  const [notificationMsg, setNotificationMsg] = useState<string | null>(null);

  const loadEvents = async () => {
    setLoadingEvents(true);
    try {
      const feed = await fetchRecentEvents(30);
      setEvents(feed);
    } catch (err) {
      console.error("Failed to load events:", err);
    } finally {
      setLoadingEvents(false);
    }
  };

  useEffect(() => {
    loadEvents();
  }, []);

  const handleCopy = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const handleSimulateMobile = async (type: "otp" | "battery") => {
    setSimulating(true);
    setNotificationMsg(null);
    try {
      if (type === "otp") {
        await triggerMobileSimulation("sms_received", {
          sender: "HDFC-BANK",
          text: "Your secret OTP for payment authorization is 948201. Valid for 5 mins.",
        });
        setNotificationMsg("Simulated Bank OTP SMS sent! Check the Notification Bell icon in the Navbar.");
      } else {
        await triggerMobileSimulation("battery_alert", {
          battery_level: 10,
        });
        setNotificationMsg("Simulated Low Battery Alert (10%) sent! Check Notification Center.");
      }
      loadEvents();
    } catch (err: any) {
      setNotificationMsg(`Simulation failed: ${err.message}`);
    } finally {
      setSimulating(false);
    }
  };

  const mobileWebhookUrl = `${API_BASE}/v1/mobile/webhook`;
  const githubWebhookUrl = `${API_BASE}/v1/webhooks/github`;
  const slackWebhookUrl = `${API_BASE}/v1/webhooks/slack`;

  return (
    <div className="h-full flex flex-col space-y-4 overflow-y-auto pr-1">
      {/* Header */}
      <div className="flex items-center justify-between bg-slate-900/60 border border-slate-800/80 backdrop-blur-md rounded-2xl p-4 px-6 shadow-lg">
        <div className="flex items-center space-x-3.5">
          <div className="w-10 h-10 rounded-xl bg-purple-500/10 border border-purple-500/30 flex items-center justify-center text-purple-400">
            <Radio className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-base font-semibold text-white tracking-wide flex items-center space-x-2">
              <span>Event Bus & Mobile Automation Hub</span>
              <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30">
                Phase 7 Active
              </span>
            </h1>
            <p className="text-xs text-slate-400">
              Redis Streams event streaming, smartphone bridges (MacroDroid/Tasker), and inbound webhook listeners.
            </p>
          </div>
        </div>

        <button
          onClick={loadEvents}
          disabled={loadingEvents}
          className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl text-xs font-medium text-slate-300 bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700/60 transition-all cursor-pointer"
        >
          <RotateCw className={`w-3.5 h-3.5 ${loadingEvents ? "animate-spin text-purple-400" : ""}`} />
          <span>Refresh Feed</span>
        </button>
      </div>

      {/* Alert Banner */}
      {notificationMsg && (
        <div className="p-3 px-4 rounded-xl bg-purple-950/40 border border-purple-500/30 text-purple-200 text-xs flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Sparkles className="w-4 h-4 text-purple-400" />
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

      {/* Top Cards: Mobile Companion & Webhook Endpoints */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Mobile Phone Card */}
        <div className="p-5 rounded-2xl bg-slate-900/50 border border-slate-800 space-y-3.5">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2.5">
              <div className="p-2 rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                <Smartphone className="w-4 h-4" />
              </div>
              <div>
                <h2 className="text-sm font-semibold text-white">Smartphone Companion Bridge</h2>
                <p className="text-[11px] text-slate-400">MacroDroid / Tasker / Apple Shortcuts Webhook</p>
              </div>
            </div>
            <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/30 font-medium">
              READY
            </span>
          </div>

          <div className="p-2.5 rounded-xl bg-slate-950/70 border border-slate-800 flex items-center justify-between">
            <code className="text-xs font-mono text-slate-300 truncate max-w-[280px]">
              {mobileWebhookUrl}
            </code>
            <button
              onClick={() => handleCopy(mobileWebhookUrl, "mobile")}
              className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs flex items-center space-x-1"
            >
              {copiedKey === "mobile" ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            </button>
          </div>

          <div className="pt-1 flex items-center space-x-2">
            <button
              onClick={() => handleSimulateMobile("otp")}
              disabled={simulating}
              className="flex-1 py-1.5 px-2.5 rounded-xl text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-all flex items-center justify-center space-x-1.5 cursor-pointer"
            >
              {simulating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5 text-cyan-400" />}
              <span>Test SMS OTP Alert</span>
            </button>
            <button
              onClick={() => handleSimulateMobile("battery")}
              disabled={simulating}
              className="flex-1 py-1.5 px-2.5 rounded-xl text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-all flex items-center justify-center space-x-1.5 cursor-pointer"
            >
              {simulating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Zap className="w-3.5 h-3.5 text-amber-400" />}
              <span>Test Low Battery Alert</span>
            </button>
          </div>
        </div>

        {/* GitHub & Slack Webhooks Card */}
        <div className="p-5 rounded-2xl bg-slate-900/50 border border-slate-800 space-y-3.5">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2.5">
              <div className="p-2 rounded-lg bg-purple-500/10 text-purple-400 border border-purple-500/20">
                <Webhook className="w-4 h-4" />
              </div>
              <div>
                <h2 className="text-sm font-semibold text-white">External Inbound Webhooks</h2>
                <p className="text-[11px] text-slate-400">Trigger workflows on GitHub & Slack events</p>
              </div>
            </div>
            <span className="text-[10px] px-2 py-0.5 rounded bg-purple-500/10 text-purple-300 border border-purple-500/30 font-medium">
              STREAM ACTIVE
            </span>
          </div>

          <div className="space-y-2">
            <div className="p-2 rounded-xl bg-slate-950/70 border border-slate-800 flex items-center justify-between">
              <span className="text-[11px] text-slate-400 font-medium">GitHub:</span>
              <code className="text-xs font-mono text-slate-300 truncate max-w-[240px]">
                {githubWebhookUrl}
              </code>
              <button
                onClick={() => handleCopy(githubWebhookUrl, "github")}
                className="p-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300"
              >
                {copiedKey === "github" ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              </button>
            </div>

            <div className="p-2 rounded-xl bg-slate-950/70 border border-slate-800 flex items-center justify-between">
              <span className="text-[11px] text-slate-400 font-medium">Slack:</span>
              <code className="text-xs font-mono text-slate-300 truncate max-w-[240px]">
                {slackWebhookUrl}
              </code>
              <button
                onClick={() => handleCopy(slackWebhookUrl, "slack")}
                className="p-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300"
              >
                {copiedKey === "slack" ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Live Redis Streams Event Feed */}
      <div className="flex-1 bg-slate-900/50 border border-slate-800 rounded-2xl p-5 flex flex-col min-h-[350px]">
        <div className="flex items-center justify-between pb-3.5 border-b border-slate-800">
          <div className="flex items-center space-x-2">
            <Activity className="w-4 h-4 text-purple-400" />
            <h2 className="text-sm font-semibold text-white">Live Event Stream (Redis Streams)</h2>
            <span className="text-xs text-slate-500 font-mono">({events.length} captured events)</span>
          </div>
          <div className="flex items-center space-x-1.5 text-xs text-emerald-400">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>Listening</span>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto space-y-2.5 pt-3 pr-1">
          {loadingEvents ? (
            <div className="py-16 text-center">
              <Loader2 className="w-6 h-6 text-purple-400 animate-spin mx-auto mb-2" />
              <p className="text-xs text-slate-400">Fetching live event stream...</p>
            </div>
          ) : events.length === 0 ? (
            <div className="py-16 text-center text-slate-500 text-xs">
              No events recorded in stream yet. Use the test simulation buttons above to trigger an event.
            </div>
          ) : (
            events.map((ev, idx) => (
              <div
                key={ev.event_id || idx}
                className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-slate-700 transition-all text-xs space-y-1.5"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-purple-500/10 text-purple-300 border border-purple-500/20">
                      {ev.topic}
                    </span>
                    <span className="text-slate-400 text-[11px]">source: <strong className="text-slate-200">{ev.source}</strong></span>
                  </div>

                  <div className="flex items-center space-x-1 text-slate-500 text-[11px]">
                    <Clock className="w-3 h-3" />
                    <span>{ev.timestamp ? new Date(ev.timestamp).toLocaleTimeString() : "recent"}</span>
                  </div>
                </div>

                <pre className="p-2 rounded-lg bg-slate-900/90 text-slate-300 font-mono text-[10px] overflow-x-auto max-h-24">
                  {JSON.stringify(ev.data, null, 2)}
                </pre>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
export default WebhooksHub;

