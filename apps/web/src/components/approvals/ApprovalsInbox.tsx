"use client";

import React, { useEffect, useState } from "react";
import { ShieldAlert, Check, X, Clock, AlertTriangle, RefreshCw } from "lucide-react";
import { fetchApprovals, respondApproval } from "@/lib/api";

interface ApprovalsInboxProps {
  onCountChange?: (count: number) => void;
}

export const ApprovalsInbox: React.FC<ApprovalsInboxProps> = ({ onCountChange }) => {
  const [approvals, setApprovals] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [processingId, setProcessingId] = useState<string | null>(null);

  const loadApprovals = async () => {
    setLoading(true);
    try {
      const list = await fetchApprovals("PENDING");
      setApprovals(list);
      if (onCountChange) {
        onCountChange(list.length);
      }
    } catch (e) {
      console.error("Failed to load approvals", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadApprovals();
  }, []);

  const handleDecision = async (id: string, decision: "approved" | "denied") => {
    setProcessingId(id);
    try {
      const ok = await respondApproval(id, decision);
      if (ok) {
        setApprovals(approvals.filter((a) => a.id !== id));
        if (onCountChange) {
          onCountChange(approvals.length - 1);
        }
      }
    } catch (e) {
      alert(`Failed to submit decision: ${e}`);
    } finally {
      setProcessingId(null);
    }
  };

  return (
    <div className="h-full flex flex-col bg-slate-900/40 rounded-2xl border border-slate-800/80 overflow-hidden shadow-2xl backdrop-blur-sm">
      {/* Header */}
      <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/40">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400">
            <ShieldAlert className="w-4 h-4" />
          </div>
          <div>
            <h3 className="font-semibold text-sm text-slate-100">Human-In-The-Loop Approvals Inbox</h3>
            <p className="text-xs text-slate-400">Review pending sensitive or destructive side-effects</p>
          </div>
        </div>

        <button
          onClick={loadApprovals}
          disabled={loading}
          className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-all"
          title="Refresh pending approvals"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {/* Content Feed */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {approvals.length > 0 ? (
          approvals.map((item) => (
            <div
              key={item.id}
              className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 space-y-3 shadow-lg hover:border-slate-700 transition-all"
            >
              <div className="flex items-start justify-between">
                <div className="space-y-1">
                  <div className="flex items-center space-x-2">
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30">
                      PENDING REVIEW
                    </span>
                    <span className="text-xs font-semibold text-slate-200">
                      {item.summary?.capability || "Sensitive Operation"}
                    </span>
                  </div>
                  <p className="text-sm font-medium text-slate-100">{item.summary?.what || "Confirmation required"}</p>
                </div>
                <span className="text-[11px] text-slate-500 flex items-center space-x-1">
                  <Clock className="w-3 h-3" />
                  <span>{new Date(item.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
                </span>
              </div>

              {/* Payload Diff or Params */}
              {item.summary?.diff && (
                <div className="bg-slate-950 rounded-xl p-3 font-mono text-xs text-slate-300 border border-slate-800">
                  <pre className="whitespace-pre-wrap">{JSON.stringify(item.summary.diff, null, 2)}</pre>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex items-center justify-end space-x-3 pt-2">
                <button
                  onClick={() => handleDecision(item.id, "denied")}
                  disabled={processingId === item.id}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-rose-500/20 text-slate-300 hover:text-rose-300 border border-slate-700 hover:border-rose-500/30 flex items-center space-x-1.5 transition-all"
                >
                  <X className="w-3.5 h-3.5" />
                  <span>Deny & Cancel</span>
                </button>
                <button
                  onClick={() => handleDecision(item.id, "approved")}
                  disabled={processingId === item.id}
                  className="px-5 py-2 rounded-xl text-xs font-semibold bg-emerald-500 hover:bg-emerald-400 text-slate-950 flex items-center space-x-1.5 transition-all shadow-lg shadow-emerald-500/20"
                >
                  <Check className="w-3.5 h-3.5" />
                  <span>Approve & Execute</span>
                </button>
              </div>
            </div>
          ))
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-center space-y-3">
            <div className="w-12 h-12 rounded-full bg-slate-800/80 border border-slate-700 flex items-center justify-center text-slate-500">
              <Check className="w-6 h-6 text-emerald-400" />
            </div>
            <div>
              <h4 className="text-sm font-semibold text-slate-300">All Clear</h4>
              <p className="text-xs text-slate-500">No pending approvals requiring your attention.</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

