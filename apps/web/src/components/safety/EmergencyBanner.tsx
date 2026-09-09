"use client";

import React, { useEffect, useState } from "react";
import { AlertOctagon, RefreshCw, ShieldAlert } from "lucide-react";
import { fetchSafetyStatus, toggleKillSwitch } from "@/lib/api";

export const EmergencyBanner: React.FC = () => {
  const [isKilled, setIsKilled] = useState<boolean>(false);
  const [killReason, setKillReason] = useState<string>("");
  const [isResuming, setIsResuming] = useState<boolean>(false);

  const checkStatus = async () => {
    try {
      const data = await fetchSafetyStatus();
      if (data && data.kill_switch) {
        setIsKilled(Boolean(data.kill_switch.active));
        setKillReason(data.kill_switch.reason || "System-wide lockdown active");
      }
    } catch {
      // Offline/quiet fallback
    }
  };

  useEffect(() => {
    checkStatus();
    const interval = setInterval(checkStatus, 4000);
    return () => clearInterval(interval);
  }, []);

  const handleResume = async () => {
    setIsResuming(true);
    try {
      const ok = await toggleKillSwitch(false);
      if (ok) {
        setIsKilled(false);
      }
    } finally {
      setIsResuming(false);
    }
  };

  if (!isKilled) return null;

  return (
    <div className="bg-rose-950/90 border-b-2 border-rose-500 text-rose-100 px-6 py-2.5 flex items-center justify-between shadow-2xl shadow-rose-950/50 backdrop-blur-md animate-pulse z-[60] sticky top-0">
      <div className="flex items-center space-x-3">
        <div className="p-1.5 rounded-lg bg-rose-500/20 border border-rose-500/40 text-rose-400">
          <AlertOctagon className="w-5 h-5 animate-bounce" />
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <span className="font-bold text-sm tracking-wide text-rose-300 uppercase">
              Emergency Kill Switch Active
            </span>
            <span className="text-[10px] uppercase font-semibold bg-rose-500 text-slate-950 px-2 py-0.5 rounded">
              Locked Down
            </span>
          </div>
          <p className="text-xs text-rose-200/80">
            {killReason} — All autonomous tool executions, workflows, and mutations are currently halted.
          </p>
        </div>
      </div>

      <button
        onClick={handleResume}
        disabled={isResuming}
        className="flex items-center space-x-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 active:scale-95 text-white font-bold text-xs rounded-xl shadow-lg shadow-emerald-600/30 transition-all cursor-pointer"
      >
        <RefreshCw className={`w-3.5 h-3.5 ${isResuming ? "animate-spin" : ""}`} />
        <span>{isResuming ? "Resuming..." : "RESUME SYSTEM"}</span>
      </button>
    </div>
  );
};

