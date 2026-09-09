"use client";

import React, { useState, useEffect } from "react";
import {
  Bell,
  X,
  Sparkles,
  Calendar,
  Mail,
  Volume2,
  Check,
  CheckCheck,
  RefreshCw,
  AlertTriangle,
} from "lucide-react";
import {
  AppNotification,
  fetchNotifications,
  markNotificationRead,
  markAllNotificationsRead,
  triggerProactiveScan,
} from "@/lib/api";
import { playBase64Audio } from "@/lib/audio";

interface NotificationCenterProps {
  isOpen: boolean;
  onClose: () => void;
  onUnreadChange?: (count: number) => void;
}

export default function NotificationCenter({
  isOpen,
  onClose,
  onUnreadChange,
}: NotificationCenterProps) {
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [isScanning, setIsScanning] = useState<boolean>(false);
  const [playingId, setPlayingId] = useState<string | null>(null);

  const loadNotifications = async () => {
    try {
      const data = await fetchNotifications();
      setNotifications(data.notifications || []);
      setUnreadCount(data.unread_count || 0);
      if (onUnreadChange) onUnreadChange(data.unread_count || 0);
    } catch (err) {
      console.error("Failed to load notifications:", err);
    }
  };

  useEffect(() => {
    loadNotifications();
    const interval = setInterval(loadNotifications, 30000); // Poll every 30s
    return () => clearInterval(interval);
  }, []);

  const handleMarkRead = async (id: string) => {
    await markNotificationRead(id);
    loadNotifications();
  };

  const handleMarkAllRead = async () => {
    await markAllNotificationsRead();
    loadNotifications();
  };

  const handleScanNow = async () => {
    setIsScanning(true);
    try {
      await triggerProactiveScan(true, true);
      await loadNotifications();
    } catch (err) {
      console.error("Proactive scan failed:", err);
    } finally {
      setIsScanning(false);
    }
  };

  const handlePlayAudio = async (notif: AppNotification) => {
    if (!notif.audio_base64) return;
    setPlayingId(notif.id);
    try {
      await playBase64Audio(notif.audio_base64);
    } finally {
      setPlayingId(null);
    }
  };

  if (!isOpen) return null;

  const getIcon = (type: string) => {
    switch (type) {
      case "BRIEFING":
        return <Sparkles className="w-4 h-4 text-purple-400" />;
      case "REMINDER":
        return <Calendar className="w-4 h-4 text-amber-400" />;
      case "INBOX_ALERT":
        return <Mail className="w-4 h-4 text-cyan-400" />;
      default:
        return <Bell className="w-4 h-4 text-slate-400" />;
    }
  };

  const getBadgeClass = (type: string) => {
    switch (type) {
      case "BRIEFING":
        return "bg-purple-500/20 text-purple-300 border-purple-500/40";
      case "REMINDER":
        return "bg-amber-500/20 text-amber-300 border-amber-500/40";
      case "INBOX_ALERT":
        return "bg-cyan-500/20 text-cyan-300 border-cyan-500/40";
      default:
        return "bg-slate-500/20 text-slate-300 border-slate-500/40";
    }
  };

  return (
    <div className="fixed inset-y-0 right-0 z-50 w-96 max-w-full bg-slate-900/95 backdrop-blur-xl border-l border-slate-800 shadow-2xl flex flex-col transition-all">
      {/* Header */}
      <div className="p-4 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
            <Bell className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white tracking-wide">
              Proactive Alerts
            </h3>
            <p className="text-xs text-slate-400">
              {unreadCount > 0 ? `${unreadCount} unread items` : "All caught up"}
            </p>
          </div>
        </div>

        <button
          onClick={onClose}
          className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Action Bar */}
      <div className="px-4 py-2 bg-slate-950/60 border-b border-slate-800 flex items-center justify-between text-xs">
        <button
          onClick={handleScanNow}
          disabled={isScanning}
          className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-indigo-600/30 hover:bg-indigo-600/50 text-indigo-300 border border-indigo-500/30 transition disabled:opacity-50"
        >
          <RefreshCw className={`w-3 h-3 ${isScanning ? "animate-spin" : ""}`} />
          {isScanning ? "Scanning..." : "Scan Now"}
        </button>

        {unreadCount > 0 && (
          <button
            onClick={handleMarkAllRead}
            className="flex items-center gap-1 text-slate-400 hover:text-slate-200 transition"
          >
            <CheckCheck className="w-3.5 h-3.5" />
            Mark all read
          </button>
        )}
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {notifications.length === 0 ? (
          <div className="text-center py-12 text-slate-500 text-xs">
            <Sparkles className="w-8 h-8 mx-auto mb-2 opacity-30" />
            No notifications yet. Click "Scan Now" to run a proactive check!
          </div>
        ) : (
          notifications.map((notif) => (
            <div
              key={notif.id}
              className={`p-3.5 rounded-xl border transition-all ${
                notif.status === "UNREAD"
                  ? "bg-slate-800/80 border-indigo-500/40 shadow-lg shadow-indigo-950/20"
                  : "bg-slate-900/40 border-slate-800/70 opacity-70"
              }`}
            >
              <div className="flex items-start justify-between gap-2 mb-1.5">
                <div className="flex items-center gap-1.5">
                  {getIcon(notif.type)}
                  <span
                    className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded border ${getBadgeClass(
                      notif.type
                    )}`}
                  >
                    {notif.type.replace("_", " ")}
                  </span>
                </div>
                <span className="text-[10px] text-slate-500 font-mono">
                  {notif.created_at ? new Date(notif.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ""}
                </span>
              </div>

              <h4 className="text-xs font-semibold text-slate-200 mb-1 leading-snug">
                {notif.title}
              </h4>

              <p className="text-[11px] text-slate-400 mb-3 whitespace-pre-line leading-relaxed">
                {notif.message}
              </p>

              <div className="flex items-center justify-between pt-2 border-t border-slate-800/80">
                {notif.audio_base64 ? (
                  <button
                    onClick={() => handlePlayAudio(notif)}
                    disabled={playingId === notif.id}
                    className="flex items-center gap-1 px-2 py-0.5 rounded text-[11px] bg-indigo-500/20 hover:bg-indigo-500/40 text-indigo-300 border border-indigo-500/30 transition disabled:opacity-50"
                  >
                    <Volume2 className={`w-3 h-3 ${playingId === notif.id ? "animate-bounce" : ""}`} />
                    {playingId === notif.id ? "Playing..." : "Listen"}
                  </button>
                ) : (
                  <span />
                )}

                {notif.status === "UNREAD" && (
                  <button
                    onClick={() => handleMarkRead(notif.id)}
                    className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-emerald-400 transition"
                  >
                    <Check className="w-3 h-3" />
                    Mark read
                  </button>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

