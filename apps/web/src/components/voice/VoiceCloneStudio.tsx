"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  fetchVoiceProfile,
  uploadVoiceSample,
  previewClonedVoice,
  activateClonedVoice,
  VoiceProfileData,
  API_BASE,
} from "@/lib/api";
import {
  Mic,
  Square,
  Upload,
  Play,
  CheckCircle2,
  Sparkles,
  Volume2,
  X,
  Radio,
  FileAudio,
  Activity,
  RefreshCw,
} from "lucide-react";

interface VoiceCloneStudioProps {
  isOpen: boolean;
  onClose: () => void;
  onVoiceActivated?: (voiceName: string) => void;
}

export const VoiceCloneStudio: React.FC<VoiceCloneStudioProps> = ({
  isOpen,
  onClose,
  onVoiceActivated,
}) => {
  const [activeMode, setActiveMode] = useState<"upload" | "record">("upload");
  const [profile, setProfile] = useState<VoiceProfileData | null>(null);
  const [hasRefAudio, setHasRefAudio] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [recordTime, setRecordTime] = useState(0);
  const [analyzing, setAnalyzing] = useState(false);
  const [previewText, setPreviewText] = useState("नमस्ते! मैं आपकी नई क्लोन की गई आवाज़ में बात कर रही हूँ।");
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewAudioUrl, setPreviewAudioUrl] = useState<string | null>(null);
  const [isActivated, setIsActivated] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (isOpen) {
      loadCurrentProfile();
    }
  }, [isOpen]);

  async function loadCurrentProfile() {
    try {
      const data = await fetchVoiceProfile();
      if (data && data.profile) {
        setProfile(data.profile);
        setHasRefAudio(data.has_reference_audio);
        setIsActivated(data.active_voice === "custom_clone");
      }
    } catch (err: any) {
      console.error("Failed to load voice profile:", err);
    }
  }

  // Handle File Upload
  async function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    setAnalyzing(true);
    setError(null);

    const reader = new FileReader();
    reader.onload = async () => {
      try {
        const base64Audio = reader.result as string;
        const newProfile = await uploadVoiceSample(base64Audio, file.name);
        setProfile(newProfile);
        setHasRefAudio(true);
        setIsActivated(false);
      } catch (err: any) {
        setError(err.message || "Failed to analyze audio sample");
      } finally {
        setAnalyzing(false);
      }
    };
    reader.readAsDataURL(file);
  }

  // Handle Microphone Recording
  async function startRecording() {
    try {
      setError(null);
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/wav" });
        stream.getTracks().forEach((track) => track.stop());

        // Convert Blob to Base64
        const reader = new FileReader();
        reader.onloadend = async () => {
          setAnalyzing(true);
          try {
            const base64Audio = reader.result as string;
            const newProfile = await uploadVoiceSample(base64Audio, "mic_recording.wav");
            setProfile(newProfile);
            setHasRefAudio(true);
            setIsActivated(false);
          } catch (err: any) {
            setError(err.message || "Failed to analyze recording");
          } finally {
            setAnalyzing(false);
          }
        };
        reader.readAsDataURL(audioBlob);
      };

      mediaRecorder.start();
      setIsRecording(true);
      setRecordTime(0);

      timerRef.current = setInterval(() => {
        setRecordTime((prev) => {
          if (prev >= 15) {
            stopRecording();
            return 15;
          }
          return prev + 1;
        });
      }, 1000);
    } catch (err: any) {
      setError("Microphone access denied or not available in your browser.");
    }
  }

  function stopRecording() {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    }
  }

  // Preview Voice Synthesis
  async function handleTestPreview() {
    if (!previewText.trim()) return;
    setPreviewLoading(true);
    setError(null);
    try {
      const audioB64 = await previewClonedVoice(previewText);
      const audioUrl = `data:audio/mp3;base64,${audioB64}`;
      setPreviewAudioUrl(audioUrl);
      const audio = new Audio(audioUrl);
      audio.play();
    } catch (err: any) {
      setError(err.message || "Failed to synthesize preview");
    } finally {
      setPreviewLoading(false);
    }
  }

  // Activate Cloned Voice
  async function handleActivate() {
    try {
      const success = await activateClonedVoice();
      if (success) {
        setIsActivated(true);
        if (onVoiceActivated) {
          onVoiceActivated("custom_clone");
        }
      }
    } catch (err: any) {
      setError(err.message || "Failed to activate cloned voice");
    }
  }

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4 animate-in fade-in duration-150">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-2xl overflow-hidden shadow-2xl flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-purple-500/10 border border-purple-500/30 flex items-center justify-center text-purple-400 shadow-md">
              <Radio className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-white text-base">Voice Clone Studio</h3>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300 font-semibold border border-purple-500/30">
                  Zero-Shot Neural Cloner
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Clone any voice from an audio sample file or live microphone recording.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-5 overflow-y-auto space-y-4 flex-1">
          {error && (
            <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-400 text-xs">
              {error}
            </div>
          )}

          {/* Mode Selector */}
          <div className="flex bg-slate-950 p-1 rounded-xl border border-slate-800">
            <button
              onClick={() => setActiveMode("upload")}
              className={`flex-1 py-2 text-xs font-semibold rounded-lg transition-all flex items-center justify-center gap-2 ${
                activeMode === "upload"
                  ? "bg-purple-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              <Upload className="w-4 h-4" />
              Upload Audio Sample (MP3 / WAV)
            </button>
            <button
              onClick={() => setActiveMode("record")}
              className={`flex-1 py-2 text-xs font-semibold rounded-lg transition-all flex items-center justify-center gap-2 ${
                activeMode === "record"
                  ? "bg-purple-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              <Mic className="w-4 h-4" />
              Record from Microphone
            </button>
          </div>

          {/* Upload Drop Zone */}
          {activeMode === "upload" && (
            <label className="border-2 border-dashed border-slate-700 hover:border-purple-500/60 bg-slate-950/40 hover:bg-purple-500/5 rounded-xl p-6 flex flex-col items-center justify-center cursor-pointer transition-all">
              <input
                type="file"
                accept="audio/*"
                onChange={handleFileSelect}
                className="hidden"
                disabled={analyzing}
              />
              <FileAudio className="w-10 h-10 text-purple-400 mb-2" />
              <span className="text-xs font-semibold text-white">Click or drag & drop audio sample</span>
              <span className="text-[11px] text-slate-500 mt-1">Supports WAV, MP3, M4A, OGG (5 to 30 seconds recommended)</span>
              {analyzing && (
                <div className="flex items-center gap-2 text-xs text-purple-300 mt-3 animate-pulse">
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  Analyzing acoustic characteristics & pitch...
                </div>
              )}
            </label>
          )}

          {/* Microphone Recorder */}
          {activeMode === "record" && (
            <div className="bg-slate-950/40 border border-slate-800 rounded-xl p-6 flex flex-col items-center justify-center text-center space-y-3">
              <div
                className={`w-16 h-16 rounded-full flex items-center justify-center transition-all ${
                  isRecording
                    ? "bg-rose-500/20 border-2 border-rose-500 text-rose-400 animate-pulse"
                    : "bg-purple-500/10 border border-purple-500/30 text-purple-400"
                }`}
              >
                <Mic className="w-7 h-7" />
              </div>

              {isRecording ? (
                <div>
                  <div className="text-sm font-bold text-rose-400">Recording... {recordTime}s / 15s</div>
                  <p className="text-[11px] text-slate-400 mt-0.5">Speak clearly into your microphone</p>
                </div>
              ) : (
                <div>
                  <div className="text-xs font-semibold text-white">Record Your Voice Sample</div>
                  <p className="text-[11px] text-slate-500 mt-0.5">Speak 5-10 seconds of any sentence</p>
                </div>
              )}

              {isRecording ? (
                <button
                  onClick={stopRecording}
                  className="px-5 py-2 bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold rounded-lg flex items-center gap-2 shadow-md transition-all"
                >
                  <Square className="w-3.5 h-3.5 fill-white" />
                  Stop & Extract Voice
                </button>
              ) : (
                <button
                  onClick={startRecording}
                  disabled={analyzing}
                  className="px-5 py-2 bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold rounded-lg flex items-center gap-2 shadow-md transition-all"
                >
                  <Mic className="w-3.5 h-3.5" />
                  Start Recording
                </button>
              )}

              {analyzing && (
                <div className="flex items-center gap-2 text-xs text-purple-300 animate-pulse">
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  Analyzing acoustic characteristics...
                </div>
              )}
            </div>
          )}

          {/* Acoustic Profile Metrics Card */}
          {profile && (
            <div className="bg-gradient-to-br from-slate-950 via-purple-950/20 to-slate-950 border border-purple-500/30 rounded-xl p-4 shadow-md space-y-3">
              <div className="flex items-center justify-between border-b border-purple-500/20 pb-2">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-purple-400" />
                  <span className="text-xs font-bold text-white uppercase tracking-wider">
                    Extracted Acoustic Characteristics
                  </span>
                </div>
                {hasRefAudio && (
                  <audio
                    src={`${API_BASE}/v1/voice/sample-audio`}
                    controls
                    className="h-7 w-48 text-xs"
                  />
                )}
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
                <div className="bg-slate-900/80 p-2.5 rounded-lg border border-slate-800">
                  <span className="text-[10px] text-slate-500 block">Fundamental Pitch (F0)</span>
                  <span className="font-bold text-white text-sm">{profile.detected_pitch_hz} Hz</span>
                </div>
                <div className="bg-slate-900/80 p-2.5 rounded-lg border border-slate-800">
                  <span className="text-[10px] text-slate-500 block">Tonal Warmth</span>
                  <span className="font-semibold text-purple-300 text-xs truncate block">{profile.tonal_profile}</span>
                </div>
                <div className="bg-slate-900/80 p-2.5 rounded-lg border border-slate-800">
                  <span className="text-[10px] text-slate-500 block">Pitch Tuning</span>
                  <span className="font-mono text-emerald-400 font-bold">{profile.pitch_adjustment}</span>
                </div>
                <div className="bg-slate-900/80 p-2.5 rounded-lg border border-slate-800">
                  <span className="text-[10px] text-slate-500 block">Sample Duration</span>
                  <span className="font-semibold text-white">{profile.duration_sec}s</span>
                </div>
              </div>

              {/* Test Bench Player */}
              <div className="pt-2 space-y-2">
                <label className="text-[11px] font-semibold text-slate-300 flex items-center gap-1.5">
                  <Volume2 className="w-3.5 h-3.5 text-indigo-400" />
                  Test Cloned Speech Before Saving
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={previewText}
                    onChange={(e) => setPreviewText(e.target.value)}
                    className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-purple-500"
                    placeholder="Enter sentence in Hindi or English..."
                  />
                  <button
                    onClick={handleTestPreview}
                    disabled={previewLoading || !previewText.trim()}
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-semibold rounded-lg flex items-center gap-1.5 transition-all"
                  >
                    {previewLoading ? (
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <Play className="w-3.5 h-3.5 fill-white" />
                    )}
                    Listen
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer Actions */}
        <div className="p-4 border-t border-slate-800 bg-slate-950/60 flex items-center justify-between">
          <button
            onClick={onClose}
            className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-white transition-colors"
          >
            Cancel
          </button>

          {profile && (
            <button
              onClick={handleActivate}
              disabled={isActivated}
              className={`px-5 py-2 text-xs font-bold rounded-lg flex items-center gap-2 shadow-lg transition-all ${
                isActivated
                  ? "bg-emerald-600 text-white cursor-default"
                  : "bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white"
              }`}
            >
              <CheckCircle2 className="w-4 h-4" />
              {isActivated ? "Activated as Friday's Voice" : "Set as Active Friday Voice"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

