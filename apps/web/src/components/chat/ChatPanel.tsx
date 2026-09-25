"use client";

import React, { useState, useEffect, useRef } from "react";
import { Send, Mic, Square, Volume2, Bot, User, CheckCircle, AlertTriangle, Clock, ShieldAlert } from "lucide-react";
import { sendChatMessageStream, ChatResponse } from "@/lib/api";
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
    
    // Add user message AND an empty bot message immediately
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
        text: "", // Will be filled via streaming
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      }
    ];
    
    setMessages(initialMessages);
    setInputText("");
    setIsLoading(true);
    setStreamStatus(null);

    // Resume local host engine in case it was halted
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
          }
        },
        !isVoiceMuted,
        selectedVoice
      );
    } catch (err) {
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
    <div className="flex flex-col h-full min-h-0 bg-slate-900/40 rounded-2xl border border-slate-800/80 overflow-hidden shadow-2xl backdrop-blur-sm">
      {/* Header Bar */}
      <div className="px-5 py-3.5 border-b border-slate-800 flex items-center justify-between bg-slate-950/40">
        <div className="flex items-center space-x-3">
          <div
            className={`w-8 h-8 rounded-full bg-cyan-500/10 border border-cyan-400/40 flex items-center justify-center text-cyan-400 transition-all ${
              isSpeaking || isLoading ? "speaking-pulse border-cyan-400 text-cyan-300" : ""
            }`}
          >
            <Bot className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-semibold text-sm text-slate-100">Live Dialogue</span>
              {isSpeaking && (
                <span className="text-[10px] bg-cyan-500/20 text-cyan-300 px-2 py-0.5 rounded-full border border-cyan-500/30 flex items-center space-x-1 animate-pulse">
                  <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
                  <span>Speaking...</span>
                </span>
              )}
              {!isSpeaking && streamStatus && (
                <span className="text-[10px] bg-amber-500/20 text-amber-300 px-2 py-0.5 rounded-full border border-amber-500/30 flex items-center space-x-1 animate-pulse">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                  <span>{streamStatus}</span>
                </span>
              )}
            </div>
          </div>
        </div>

        {isSpeaking && (
          <button
            onClick={stopAudio}
            className="flex items-center space-x-1.5 px-3 py-1 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border border-rose-500/40 text-xs font-semibold animate-pulse transition-all"
          >
            <Square className="w-3 h-3 fill-rose-300" />
            <span>Stop Speaking (Esc)</span>
          </button>
        )}
      </div>

      {/* Message Feed */}
      <div className="flex-1 min-h-0 overflow-y-auto p-4 space-y-4">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex items-start space-x-3 ${
              msg.sender === "user" ? "justify-end" : "justify-start"
            }`}
          >
            {msg.sender === "friday" && (
              <div className="w-7 h-7 rounded-full bg-cyan-500/10 border border-cyan-400/30 flex items-center justify-center text-cyan-400 shrink-0 mt-0.5">
                <Bot className="w-3.5 h-3.5" />
              </div>
            )}

            <div
              className={`max-w-[80%] rounded-2xl p-3.5 text-sm shadow-md leading-relaxed ${
                msg.sender === "user"
                  ? "bg-cyan-600/90 text-white rounded-tr-none"
                  : "bg-slate-900 border border-slate-800 text-slate-200 rounded-tl-none"
              }`}
            >
              <div className="flex items-center justify-between mb-1 space-x-2 text-[11px]">
                <span className="font-semibold text-slate-400">
                  {msg.sender === "user" ? "You" : "Sara"}
                </span>
                <div className="flex items-center space-x-2">
                  <span className="text-slate-500 text-[10px]">{msg.timestamp}</span>
                  {msg.audioBase64 && (
                    <button
                      onClick={() => playBase64Audio(msg.audioBase64!)}
                      className="text-cyan-400 hover:text-cyan-300 flex items-center space-x-1"
                      title="Replay Audio"
                    >
                      <Volume2 className="w-3 h-3" />
                      <span className="text-[10px]">Replay</span>
                    </button>
                  )}
                </div>
              </div>

              <p className="whitespace-pre-wrap">{msg.text}</p>

              {/* 5-Point Report Viewer */}
              {msg.report && (
                <div className="mt-3 bg-slate-950/80 border border-slate-800 rounded-xl p-3 text-xs space-y-2">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-1.5">
                    <span className="font-semibold text-slate-300">📋 Standard 5-Point Report</span>
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
                          <li key={idx}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {msg.report.important_results?.length > 0 && (
                    <div>
                      <span className="text-slate-400 font-medium">IMPORTANT RESULTS:</span>
                      <ul className="list-disc list-inside text-cyan-300 ml-1 mt-0.5 space-y-0.5">
                        {msg.report.important_results.map((item, idx) => (
                          <li key={idx}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {msg.report.any_problems?.length > 0 && (
                    <div>
                      <span className="text-rose-400 font-medium">PROBLEMS:</span>
                      <ul className="list-disc list-inside text-rose-300 ml-1 mt-0.5 space-y-0.5">
                        {msg.report.any_problems.map((item, idx) => (
                          <li key={idx}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {msg.report.actions_requiring_me?.length > 0 && (
                    <div>
                      <span className="text-amber-400 font-medium">ACTIONS REQUIRING YOU:</span>
                      <ul className="list-disc list-inside text-amber-300 ml-1 mt-0.5 space-y-0.5">
                        {msg.report.actions_requiring_me.map((item, idx) => (
                          <li key={idx}>{item}</li>
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
      <div className="px-4 py-2 border-t border-slate-800/80 bg-slate-950/40 flex flex-wrap gap-2">
        <button
          onClick={() => handleSend("Kaise ho Sara?")}
          className="text-xs bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 px-3 py-1 rounded-full transition-all"
        >
          Kaise ho Sara?
        </button>
        <button
          onClick={() => handleSend("Tum kaun ho aur kya kar sakti ho?")}
          className="text-xs bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 px-3 py-1 rounded-full transition-all"
        >
          Tum kaun ho?
        </button>
        <button
          onClick={() => handleSend("Draft an email to the marketing team about the launch kickoff")}
          className="text-xs bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 px-3 py-1 rounded-full transition-all"
        >
          Draft email to team
        </button>
        <button
          onClick={() => handleSend("Check my calendar events for today")}
          className="text-xs bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 px-3 py-1 rounded-full transition-all"
        >
          Check Calendar
        </button>
      </div>

      {/* Input Bar */}
      <div className="p-3 border-t border-slate-800 bg-slate-950/60 flex items-center space-x-2">
        <button
          onClick={toggleMic}
          className={`w-10 h-10 rounded-xl flex items-center justify-center transition-all ${
            isListening
              ? "bg-rose-500 text-white animate-pulse"
              : "bg-slate-800 hover:bg-slate-700 text-slate-300"
          }`}
          title="Voice input"
        >
          <Mic className="w-4 h-4" />
        </button>

        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          placeholder="Message or instruction for Sara (Hindi / English)..."
          className="flex-1 bg-slate-900/90 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-white placeholder-slate-500 outline-none focus:border-cyan-500/50 transition-all"
        />

        <button
          onClick={() => handleSend()}
          disabled={isLoading || !inputText.trim()}
          className="bg-cyan-500 hover:bg-cyan-400 disabled:opacity-50 text-slate-950 px-4 py-2.5 rounded-xl font-semibold text-sm flex items-center space-x-1.5 transition-all shadow-lg shadow-cyan-500/20"
        >
          <span>Send</span>
          <Send className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
};

