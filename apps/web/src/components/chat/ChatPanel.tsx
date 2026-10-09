"use client";

import React, { useState, useEffect, useRef } from "react";
import { Send, Mic, Square, Volume2, Bot, User, CheckCircle, AlertTriangle, Clock, ShieldAlert } from "lucide-react";
import { sendChatMessageStream, ChatResponse, emergencyHalt } from "@/lib/api";
import { playBase64Audio, stopAudio, subscribeSpeaking } from "@/lib/audio";

interface MessageItem {
  id: string;
  sender: "user" | "friday";
  text: string;
  report?: ChatResponse["report"];
  audioBase64?: string;
  timestamp: string;
}

interface ChatPanelProps {
  isVoiceMuted: boolean;
  selectedVoice: string;
  onTaskCreated?: (taskId: string) => void;
}

export const ChatPanel: React.FC<ChatPanelProps> = ({
  isVoiceMuted,
  selectedVoice,
  onTaskCreated,
}) => {
  const [messages, setMessages] = useState<MessageItem[]>([
    {
      id: "welcome",
      sender: "friday",
      text: "Namaste! I am Sara, your personal AI operating system assistant. All systems, security policies, and workspace tools are online. Aap mujhse Hindi ya English mein baat kar sakte hain!",
      timestamp: "Just now",
    },
  ]);
  const [inputText, setInputText] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [streamStatus, setStreamStatus] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const handleStopTask = async () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    stopAudio();
    emergencyHalt("Task stopped by user via Stop button");

    setIsLoading(false);
    setStreamStatus(null);

    setMessages((prev) => [
      ...prev,
      {
        id: `stop_${Date.now()}`,
        sender: "friday",
        text: "?? **Task Stopped**: Maine chal rahe task ko turant STOP kar diya hai. Saari operations halt ho gayi hain.",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      },
    ]);
  };

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        handleStopTask();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  useEffect(() => {
    const unsubscribe = subscribeSpeaking((speaking) => {
      setIsSpeaking(speaking);
    });
    return () => unsubscribe();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async (messageToSend?: string) => {
    const text = (messageToSend || inputText).trim();
    if (!text || isLoading) return;

    const userMessageId = `user_${Date.now()}`;
    const botMessageId = `friday_${Date.now()}`;
    
    const initialMessages: MessageItem[] = [
      ...messages,
      {
        id: userMessageId,
        sender: "user",
        text,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      },
      {
        id: botMessageId,
        sender: "friday",
        text: "",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      }
    ];
    
    setMessages(initialMessages);
    setInputText("");
    setIsLoading(true);
    setStreamStatus(null);

    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    try {
      fetch("http://127.0.0.1:8000/api/resume", { method: "POST" }).catch(() => {});
    } catch {}

    let currentText = "";
    let finalAudioBase64: string | undefined;

    try {
      await sendChatMessageStream(
        text,
        (event) => {
          if (event.type === "status") {
            setStreamStatus(event.content!);
          } else if (event.type === "progress") {
            setStreamStatus(event.content!);
          } else if (event.type === "token") {
            currentText += event.content;
            setStreamStatus(null);
            
            setMessages((prev) => 
              prev.map((msg) => 
                msg.id === botMessageId 
                  ? { ...msg, text: currentText } 
                  : msg
              )
            );
          } else if (event.type === "report") {
            setMessages((prev) => 
              prev.map((msg) => 
                msg.id === botMessageId 
                  ? { ...msg, report: event.report } 
                  : msg
              )
            );
          } else if (event.type === "audio") {
            finalAudioBase64 = event.audio_base64;
            setMessages((prev) => 
              prev.map((msg) => 
                msg.id === botMessageId 
                  ? { ...msg, audioBase64: finalAudioBase64 } 
                  : msg
              )
            );
            if (!isVoiceMuted && finalAudioBase64) {
              playBase64Audio(finalAudioBase64);
            }
          } else if (event.type === "done") {
            setIsLoading(false);
            setStreamStatus(null);
            abortControllerRef.current = null;
            if (event.task_id && onTaskCreated) {
              onTaskCreated(event.task_id);
            }
          } else if (event.type === "error") {
            setMessages((prev) => 
              prev.map((msg) => 
                msg.id === botMessageId 
                  ? { ...msg, text: currentText + "\n\n**Error:** " + ((event as any).error || event.content) } 
                  : msg
              )
            );
            setIsLoading(false);
            setStreamStatus(null);
            abortControllerRef.current = null;
          }
        },
        !isVoiceMuted,
        selectedVoice,
        abortController.signal
      );
    } catch (err: any) {
      if (err.name === "AbortError") {
        setIsLoading(false);
        setStreamStatus(null);
        abortControllerRef.current = null;
        return;
      }
      console.error("Failed to send message:", err);
      setMessages((prev) => 
        prev.map((msg) => 
          msg.id === botMessageId 
            ? { ...msg, text: "**Error:** " + (err instanceof Error ? err.message : String(err)) } 
            : msg
        )
      );
      setIsLoading(false);
      setStreamStatus(null);
      abortControllerRef.current = null;
    }
  };

  const toggleMic = () => {
    if (!("webkitSpeechRecognition" in window || "SpeechRecognition" in window)) {
      alert("Speech recognition is not supported in your browser.");
      return;
    }

    if (isListening) {
      setIsListening(false);
      return;
    }

    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = selectedVoice.startsWith("hi") ? "hi-IN" : "en-US";

    recognition.onstart = () => setIsListening(true);
    recognition.onend = () => setIsListening(false);
    recognition.onerror = () => setIsListening(false);
    recognition.onresult = (event: any) => {
      const transcript = event.results[0][0].transcript;
      setInputText(transcript);
      handleSend(transcript);
    };

    recognition.start();
  };

  return (
    <div className="flex flex-col h-full min-h-0 min-w-0 bg-slate-900/40 rounded-2xl border border-slate-800/80 overflow-hidden shadow-2xl backdrop-blur-sm">
      {/* Header Bar */}
      <div className="px-3 sm:px-5 py-3 border-b border-slate-800 flex items-center justify-between bg-slate-950/40 gap-2 shrink-0">
        <div className="flex items-center space-x-2.5 sm:space-x-3 min-w-0">
          <div
            className={`w-8 h-8 rounded-full bg-cyan-500/10 border border-cyan-400/40 flex items-center justify-center text-cyan-400 shrink-0 transition-all ${
              isSpeaking || isLoading ? "speaking-pulse border-cyan-400 text-cyan-300" : ""
            }`}
          >
            <Bot className="w-4 h-4" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center space-x-1.5 sm:space-x-2 flex-wrap">
              <span className="font-semibold text-xs sm:text-sm text-slate-100">Live Dialogue</span>
              {isSpeaking && (
                <span className="text-[10px] bg-cyan-500/20 text-cyan-300 px-2 py-0.5 rounded-full border border-cyan-500/30 flex items-center space-x-1 animate-pulse">
                  <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
                  <span>Speaking...</span>
                </span>
              )}
              {!isSpeaking && streamStatus && (
                <span className="text-[10px] bg-amber-500/20 text-amber-300 px-2 py-0.5 rounded-full border border-amber-500/30 flex items-center space-x-1 animate-pulse truncate max-w-[140px] sm:max-w-none">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-400 shrink-0" />
                  <span className="truncate">{streamStatus}</span>
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-2 shrink-0">
          {(isLoading || isSpeaking) ? (
            <button
              onClick={handleStopTask}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs shadow-lg shadow-rose-600/40 animate-pulse transition-all cursor-pointer border border-rose-400 min-h-[38px] active:scale-95"
              title="Press Esc or click to stop task immediately"
            >
              <Square className="w-3.5 h-3.5 fill-white" />
              <span>STOP (Esc)</span>
            </button>
          ) : (
            <button
              onClick={handleStopTask}
              className="flex items-center space-x-1 px-2.5 py-1.5 rounded-xl bg-slate-800/80 hover:bg-rose-950/60 text-slate-400 hover:text-rose-300 border border-slate-700/60 hover:border-rose-500/40 text-xs font-semibold transition-all cursor-pointer min-h-[38px] active:scale-95"
              title="Emergency Stop (Esc)"
            >
              <Square className="w-3 h-3 fill-slate-400" />
              <span className="hidden sm:inline">Stop</span>
            </button>
          )}
        </div>
      </div>

      {/* Message Feed */}
      <div className="flex-1 min-h-0 overflow-y-auto p-3 sm:p-4 space-y-3 sm:space-y-4">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex items-start space-x-2 sm:space-x-3 ${
              msg.sender === "user" ? "justify-end" : "justify-start"
            }`}
          >
            {msg.sender === "friday" && (
              <div className="w-7 h-7 rounded-full bg-cyan-500/10 border border-cyan-400/30 flex items-center justify-center text-cyan-400 shrink-0 mt-0.5">
                <Bot className="w-3.5 h-3.5" />
              </div>
            )}

            <div
              className={`max-w-[92%] sm:max-w-[85%] md:max-w-[80%] rounded-2xl p-3 sm:p-3.5 text-xs sm:text-sm shadow-md leading-relaxed break-words overflow-hidden ${
                msg.sender === "user"
                  ? "bg-cyan-600/90 text-white rounded-tr-none"
                  : "bg-slate-900 border border-slate-800 text-slate-200 rounded-tl-none"
              }`}
            >
              <div className="flex items-center justify-between mb-1 space-x-2 text-[11px] gap-2 flex-wrap">
                <span className="font-semibold text-slate-400">
                  {msg.sender === "user" ? "You" : "Sara"}
                </span>
                <div className="flex items-center space-x-2">
                  <span className="text-slate-500 text-[10px]">{msg.timestamp}</span>
                  {msg.audioBase64 && (
                    <button
                      onClick={() => playBase64Audio(msg.audioBase64!)}
                      className="text-cyan-400 hover:text-cyan-300 flex items-center space-x-1 cursor-pointer active:scale-95"
                      title="Replay Audio"
                    >
                      <Volume2 className="w-3 h-3" />
                      <span className="text-[10px]">Replay</span>
                    </button>
                  )}
                </div>
              </div>

              <p className="whitespace-pre-wrap break-words">{msg.text}</p>

              {/* 5-Point Report Viewer */}
              {msg.report && (
                <div className="mt-3 bg-slate-950/80 border border-slate-800 rounded-xl p-2.5 sm:p-3 text-[11px] sm:text-xs space-y-2 overflow-x-auto">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-1.5 flex-wrap gap-1">
                    <span className="font-semibold text-slate-300">?? Standard 5-Point Report</span>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        msg.report.status === "COMPLETED"
                          ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                          : "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                      }`}
                    >
                      {msg.report.status}
                    </span>
                  </div>

                  {msg.report.what_was_done?.length > 0 && (
                    <div>
                      <span className="text-slate-400 font-medium">WHAT WAS DONE:</span>
                      <ul className="list-disc list-inside text-slate-300 ml-1 mt-0.5 space-y-0.5">
                        {msg.report.what_was_done.map((item, idx) => (
                          <li key={idx} className="break-words">{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {msg.report.important_results?.length > 0 && (
                    <div>
                      <span className="text-slate-400 font-medium">IMPORTANT RESULTS:</span>
                      <ul className="list-disc list-inside text-cyan-300 ml-1 mt-0.5 space-y-0.5">
                        {msg.report.important_results.map((item, idx) => (
                          <li key={idx} className="break-words">{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {msg.report.any_problems?.length > 0 && (
                    <div>
                      <span className="text-rose-400 font-medium">PROBLEMS:</span>
                      <ul className="list-disc list-inside text-rose-300 ml-1 mt-0.5 space-y-0.5">
                        {msg.report.any_problems.map((item, idx) => (
                          <li key={idx} className="break-words">{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {msg.report.actions_requiring_me?.length > 0 && (
                    <div>
                      <span className="text-amber-400 font-medium">ACTIONS REQUIRING YOU:</span>
                      <ul className="list-disc list-inside text-amber-300 ml-1 mt-0.5 space-y-0.5">
                        {msg.report.actions_requiring_me.map((item, idx) => (
                          <li key={idx} className="break-words">{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>

            {msg.sender === "user" && (
              <div className="w-7 h-7 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 shrink-0 mt-0.5">
                <User className="w-3.5 h-3.5" />
              </div>
            )}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Quick Prompt Chips */}
      <div className="px-3 sm:px-4 py-2 border-t border-slate-800/80 bg-slate-950/40 flex items-center gap-2 overflow-x-auto scrollbar-none whitespace-nowrap shrink-0">
        <button
          onClick={() => handleSend("Kaise ho Sara?")}
          className="text-xs bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 px-3 py-1.5 rounded-full transition-all shrink-0 cursor-pointer min-h-[32px] flex items-center active:scale-95"
        >
          Kaise ho Sara?
        </button>
        <button
          onClick={() => handleSend("Tum kaun ho aur kya kar sakti ho?")}
          className="text-xs bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 px-3 py-1.5 rounded-full transition-all shrink-0 cursor-pointer min-h-[32px] flex items-center active:scale-95"
        >
          Tum kaun ho?
        </button>
        <button
          onClick={() => handleSend("Draft an email to the marketing team about the launch kickoff")}
          className="text-xs bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 px-3 py-1.5 rounded-full transition-all shrink-0 cursor-pointer min-h-[32px] flex items-center active:scale-95"
        >
          Draft email to team
        </button>
        <button
          onClick={() => handleSend("Check my calendar events for today")}
          className="text-xs bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 px-3 py-1.5 rounded-full transition-all shrink-0 cursor-pointer min-h-[32px] flex items-center active:scale-95"
        >
          Check Calendar
        </button>
      </div>

      {/* Input Bar */}
      <div className="p-2.5 sm:p-3 border-t border-slate-800 bg-slate-950/60 flex items-center space-x-2 shrink-0">
        <button
          onClick={toggleMic}
          className={`w-11 h-11 min-w-[44px] min-h-[44px] rounded-xl flex items-center justify-center transition-all shrink-0 active:scale-95 cursor-pointer ${
            isListening
              ? "bg-rose-500 text-white animate-pulse"
              : "bg-slate-800 hover:bg-slate-700 text-slate-300"
          }`}
          title="Voice input (Microphone)"
          aria-label="Toggle voice input"
        >
          <Mic className="w-5 h-5" />
        </button>

        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          placeholder="Message or instruction for Sara (Hindi / English)..."
          className="flex-1 bg-slate-900/90 border border-slate-800 rounded-xl px-3.5 sm:px-4 py-2.5 text-base sm:text-sm text-white placeholder-slate-500 outline-none focus:border-cyan-500/50 transition-all min-h-[44px] min-w-0"
        />

        {isLoading ? (
          <button
            onClick={handleStopTask}
            className="bg-rose-600 hover:bg-rose-500 text-white px-4 sm:px-5 py-2.5 rounded-xl font-bold text-xs sm:text-sm flex items-center space-x-1.5 transition-all shadow-lg shadow-rose-600/30 animate-pulse cursor-pointer border border-rose-400 min-h-[44px] shrink-0 active:scale-95"
            title="Stop running task (Esc)"
          >
            <Square className="w-3.5 h-3.5 fill-white" />
            <span>STOP</span>
          </button>
        ) : (
          <button
            onClick={() => handleSend()}
            disabled={!inputText.trim()}
            className="bg-cyan-500 hover:bg-cyan-400 disabled:opacity-50 text-slate-950 px-3.5 sm:px-4 py-2.5 rounded-xl font-semibold text-xs sm:text-sm flex items-center space-x-1.5 transition-all shadow-lg shadow-cyan-500/20 min-h-[44px] shrink-0 active:scale-95 cursor-pointer"
            aria-label="Send message"
          >
            <span className="hidden sm:inline">Send</span>
            <Send className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
};
export default ChatPanel;
