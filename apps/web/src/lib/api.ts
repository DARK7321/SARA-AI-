/**
 * OmniBrain API Client for Command Center Frontend.
 * Interacts with backend FastAPI services on http://localhost:8000.
 */

const configuredApiBase = process.env.NEXT_PUBLIC_API_BASE;

const localApiBase =
  typeof window !== "undefined" &&
  (window.location.protocol === "file:" ||
    window.location.hostname === "" ||
    window.location.hostname === "localhost" ||
    window.location.hostname === "127.0.0.1")
    ? "http://127.0.0.1:8000"
    : "https://sara-api-xdxw.onrender.com";

export const API_BASE = configuredApiBase || localApiBase;

let cachedToken: string | null = null;

export async function login(
  username = "vikas635026@gmail.com",
  password = "OmniBrain@2026"
): Promise<string> {
  const params = new URLSearchParams();
  params.append("username", username);
  params.append("password", password);

  const res = await fetch(`${API_BASE}/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: params,
  });

  if (!res.ok) {
    throw new Error(`Login failed with status ${res.status}`);
  }

  const json = await res.json();
  cachedToken = json.data?.access_token || json.access_token;
  if (!cachedToken) {
    throw new Error("No access_token found in login response");
  }
  if (typeof window !== "undefined") {
    localStorage.setItem("omnibrain_token", cachedToken);
  }
  return cachedToken;
}

export function logout() {
  cachedToken = null;
  if (typeof window !== "undefined") {
    localStorage.removeItem("omnibrain_token");
  }
}

export function getAuthToken(): string | null {
  if (cachedToken && cachedToken !== "undefined") return cachedToken;
  if (typeof window !== "undefined") {
    const t = localStorage.getItem("omnibrain_token");
    if (t && t !== "undefined") {
      cachedToken = t;
      return t;
    }
  }
  return null;
}

export async function getAuthHeaders(): Promise<Record<string, string>> {
  let token = getAuthToken();
  if (!token) {
    token = await login();
  }
  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
  };
}

export interface ChatResponse {
  reply: string;
  path: string;
  task_id?: string;
  report?: {
    status: string;
    what_was_done: string[];
    important_results: string[];
    any_problems: string[];
    actions_requiring_me: string[];
    spoken_summary: string;
  };
  audio_base64?: string;
}

export async function sendChatMessage(
  message: string,
  includeAudio = true,
  voice = "auto"
): Promise<ChatResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/v1/chat`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      message,
      include_audio: includeAudio,
      voice,
    }),
  });

  if (res.status === 401) {
    await login();
    return sendChatMessage(message, includeAudio, voice);
  }

  if (!res.ok) {
    throw new Error(`Chat API failed with status ${res.status}`);
  }

  const json = await res.json();
  return json.data;
}

export type ChatStreamCallback = (event: {
  type: "status" | "token" | "progress" | "audio" | "report" | "done" | "error";
  content?: string;
  step?: number;
  total?: number;
  audio_base64?: string;
  report?: any;
  path?: string;
  task_id?: string;
}) => void;

export async function sendChatMessageStream(
  message: string,
  onEvent: ChatStreamCallback,
  includeAudio = true,
  voice = "auto",
  signal?: AbortSignal
): Promise<void> {
  const headers = await getAuthHeaders();
  
  try {
    const res = await fetch(`${API_BASE}/v1/chat/stream`, {
      method: "POST",
      headers,
      signal,
      body: JSON.stringify({
        message,
        include_audio: includeAudio,
        voice,
      }),
    });

    if (res.status === 401) {
      logout();
      await login();
      return sendChatMessageStream(message, onEvent, includeAudio, voice, signal);
    }

    if (!res.ok) {
      throw new Error(`Chat Stream API failed with status ${res.status}`);
    }

    if (!res.body) {
      throw new Error("ReadableStream not supported by the browser or response has no body");
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      
      const lines = buffer.split("\n\n");
      buffer = lines.pop() || ""; // Keep the incomplete chunk in the buffer

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const dataStr = line.slice(6);
          if (dataStr.trim() === "[DONE]") {
            continue;
          }
          try {
            const parsed = JSON.parse(dataStr);
            onEvent(parsed);
          } catch (e) {
            console.error("Failed to parse SSE line:", dataStr, e);
          }
        }
      }
    }
    
    // Process any remaining buffer if it happens to end exactly at \n\n
    if (buffer.startsWith("data: ")) {
      try {
        const parsed = JSON.parse(buffer.slice(6));
        onEvent(parsed);
      } catch (e) {}
    }
    
  } catch (err: any) {
    if (err.name === "AbortError") {
      onEvent({ type: "status", content: "🛑 Task cancelled by user" });
      return;
    }
    console.error("Chat streaming error:", err);
    onEvent({ type: "error", content: err.message });
  }
}

export async function cancelTask(taskId: string): Promise<boolean> {
  try {
    const headers = await getAuthHeaders();
    const res = await fetch(`${API_BASE}/v1/tasks/${taskId}/cancel`, {
      method: "POST",
      headers,
    });
    return res.ok;
  } catch {
    return false;
  }
}

export async function emergencyHalt(reason = "Emergency Stop triggered by user"): Promise<boolean> {
  let ok = false;
  try {
    ok = await toggleKillSwitch(true, reason);
  } catch (e) {
    console.error("toggleKillSwitch error:", e);
  }
  try {
    await fetch("http://127.0.0.1:8000/api/stop", { method: "POST" });
  } catch {}
  return ok;
}

export async function fetchTasks(limit = 10): Promise<any[]> {
  try {
    const headers = await getAuthHeaders();
    const res = await fetch(`${API_BASE}/v1/tasks?limit=${limit}`, { headers });
    if (!res.ok) return [];
    const json = await res.json();
    return json.data?.tasks || (Array.isArray(json.data) ? json.data : []);
  } catch (err) {
    console.error("fetchTasks error:", err);
    return [];
  }
}

export async function fetchTaskDetails(taskId: string): Promise<any> {
  try {
    const headers = await getAuthHeaders();
    const res = await fetch(`${API_BASE}/v1/tasks/${taskId}`, { headers });
    if (!res.ok) return null;
    const json = await res.json();
    return json.data?.task || json.data || null;
  } catch (err) {
    console.error(`fetchTaskDetails(${taskId}) error:`, err);
    return null;
  }
}

export async function fetchApprovals(status = "PENDING"): Promise<any[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/v1/approvals?status=${status}`, { headers });
  if (!res.ok) return [];
  const json = await res.json();
  return json.data.approvals || [];
}

export async function respondApproval(approvalId: string, decision: "approved" | "denied"): Promise<boolean> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/v1/approvals/${approvalId}/respond`, {
    method: "POST",
    headers,
    body: JSON.stringify({ decision }),
  });
  return res.ok;
}

export async function fetchConnectors(): Promise<any[]> {
  try {
    let headers = await getAuthHeaders();
    let res = await fetch(`${API_BASE}/v1/connectors`, { headers });
    if (res.status === 401) {
      logout();
      headers = await getAuthHeaders();
      res = await fetch(`${API_BASE}/v1/connectors`, { headers });
    }
    if (res.ok) {
      const json = await res.json();
      return json.data?.connectors || [];
    }
  } catch (err) {
    console.warn("fetchConnectors failed on API_BASE, attempting local fallback:", err);
  }

  // Graceful fallback to local SARA engine if running on desktop
  try {
    const localRes = await fetch("http://127.0.0.1:8000/v1/connectors");
    if (localRes.ok) {
      const json = await localRes.json();
      return json.data?.connectors || [];
    }
  } catch {}

  return [];
}

export async function fetchHealthCenter(): Promise<any> {
  const res = await fetch(`${API_BASE}/v1/health/center`);
  if (!res.ok) return null;
  const json = await res.json();
  return json.data;
}

export interface AppNotification {
  id: string;
  type: string;
  title: string;
  message: string;
  spoken_text?: string;
  audio_base64?: string;
  status: "UNREAD" | "READ" | "DISMISSED";
  created_at: string;
  metadata?: Record<string, any>;
}

export async function fetchNotifications(unreadOnly = false): Promise<{ notifications: AppNotification[]; unread_count: number }> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/v1/notifications?unread_only=${unreadOnly}`, { headers });
  if (!res.ok) return { notifications: [], unread_count: 0 };
  const json = await res.json();
  return json.data;
}

export async function markNotificationRead(notificationId: string): Promise<boolean> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/v1/notifications/${notificationId}/read`, {
    method: "POST",
    headers,
  });
  return res.ok;
}

export async function markAllNotificationsRead(): Promise<boolean> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/v1/notifications/read-all`, {
    method: "POST",
    headers,
  });
  return res.ok;
}

export async function triggerProactiveScan(forceBriefing = true, includeAudio = true): Promise<{ generated_count: number; notifications: AppNotification[] }> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/v1/proactive/trigger`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      force_briefing: forceBriefing,
      include_audio: includeAudio,
    }),
  });
  if (!res.ok) throw new Error("Failed to trigger proactive scan");
  const json = await res.json();
  return json.data;
}

export interface WorkflowStep {
  id: string;
  name: string;
  connector: string;
  action: string;
  inputs?: Record<string, any>;
  depends_on?: string[];
}

export interface WorkflowDefinition {
  steps: WorkflowStep[];
}

export interface Workflow {
  id: string;
  name: string;
  description?: string;
  trigger_type: string;
  cron_expression?: string;
  is_active: boolean;
  definition: WorkflowDefinition;
  created_at: string;
  updated_at?: string;
}

export interface WorkflowRun {
  id: string;
  workflow_id: string;
  status: "RUNNING" | "COMPLETED" | "FAILED";
  started_at: string;
  finished_at?: string;
  result?: {
    step_logs?: Array<{
      step_id: string;
      step_name: string;
      action: string;
      status: string;
      data?: any;
      error?: string;
    }>;
    step_outputs?: Record<string, any>;
    total_steps?: number;
  };
  error?: {
    step_id?: string;
    error?: string;
  };
}

export async function fetchWorkflows(): Promise<{ workflows: Workflow[]; templates: any[] }> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/v1/workflows`, { headers });
  if (!res.ok) return { workflows: [], templates: [] };
  const json = await res.json();
  return json.data;
}

export async function runWorkflow(workflowId: string, customInputs?: Record<string, any>): Promise<WorkflowRun> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/v1/workflows/${workflowId}/run`, {
    method: "POST",
    headers,
    body: JSON.stringify({ custom_inputs: customInputs || null }),
  });
  if (!res.ok) throw new Error("Failed to execute workflow");
  const json = await res.json();
  return json.data;
}

export async function fetchWorkflowRuns(workflowId: string): Promise<WorkflowRun[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/v1/workflows/${workflowId}/runs`, { headers });
  if (!res.ok) return [];
  const json = await res.json();
  return json.data.runs || [];
}

export async function deleteWorkflow(workflowId: string): Promise<boolean> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/v1/workflows/${workflowId}`, {
    method: "DELETE",
    headers,
  });
  return res.ok;
}

export interface WebhookEventItem {
  msg_id?: string;
  event_id: string;
  topic: string;
  source: string;
  data: Record<string, any>;
  timestamp: string;
}

export async function fetchRecentEvents(limit = 20): Promise<WebhookEventItem[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/v1/webhooks/events?limit=${limit}`, { headers });
  if (!res.ok) return [];
  const json = await res.json();
  return json.data.events || [];
}

export async function fetchWebhooksInfo(): Promise<any> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/v1/webhooks/info`, { headers });
  if (!res.ok) return null;
  const json = await res.json();
  return json.data;
}

export async function triggerMobileSimulation(eventType: string, payload: Record<string, any>): Promise<any> {
  const res = await fetch(`${API_BASE}/v1/mobile/webhook`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ event_type: eventType, ...payload }),
  });
  if (!res.ok) throw new Error("Failed to trigger mobile event");
  const json = await res.json();
  return json.data;
}

// ==========================================
// Phase 8: Progressive Autonomy, Safety & Aliases
// ==========================================

export interface AutonomyTier {
  title: string;
  description: string;
  badge: string;
  color: string;
}

export interface AutonomySettingsData {
  current_level: number;
  current_info: AutonomyTier;
  tiers: Record<number, AutonomyTier>;
}

export async function fetchAutonomySettings(): Promise<AutonomySettingsData | null> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/v1/policies/autonomy`, { headers });
  if (!res.ok) return null;
  const json = await res.json();
  return json.data;
}

export async function updateAutonomyLevel(level: number): Promise<boolean> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/v1/policies/autonomy`, {
    method: "POST",
    headers,
    body: JSON.stringify({ autonomy_level: level }),
  });
  return res.ok;
}

export interface SafetyStatusData {
  kill_switch: {
    active: boolean;
    activated_at?: string;
    reason?: string;
    triggered_by?: string;
    resumed_by?: string;
  };
  circuit_breakers: {
    connectors: Record<
      string,
      {
        connector: string;
        state: "CLOSED" | "OPEN" | "HALF_OPEN";
        consecutive_failures: number;
        last_error?: string;
        total_calls: number;
        total_failures: number;
      }
    >;
    tripped_count: number;
    system_circuit_healthy: boolean;
  };
  autonomy_level: {
    level: number;
    info: AutonomyTier;
  };
}

export async function fetchSafetyStatus(): Promise<SafetyStatusData | null> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/v1/safety/status`, { headers });
  if (!res.ok) return null;
  const json = await res.json();
  return json.data;
}

export async function toggleKillSwitch(active: boolean, reason?: string): Promise<boolean> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/v1/safety/kill-switch`, {
    method: "POST",
    headers,
    body: JSON.stringify({ active, reason }),
  });
  return res.ok;
}

export async function resetCircuitBreaker(connector?: string): Promise<boolean> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/v1/safety/circuit-breaker/reset`, {
    method: "POST",
    headers,
    body: JSON.stringify({ connector }),
  });
  return res.ok;
}

export interface AliasItem {
  id: string;
  name: string;
  target_type: string;
  target_id?: string;
  parameters: Record<string, any>;
  is_active: boolean;
  is_builtin: boolean;
  description?: string;
  created_at?: string;
}

export async function fetchAliases(): Promise<AliasItem[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/v1/aliases`, { headers });
  if (!res.ok) return [];
  const json = await res.json();
  return json.data.aliases || [];
}

export async function createAlias(payload: {
  name: string;
  target_type: string;
  target_id: string;
  parameters?: Record<string, any>;
}): Promise<any> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/v1/aliases`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const json = await res.json();
    throw new Error(json.detail || "Failed to create alias");
  }
  const json = await res.json();
  return json.data;
}

export async function deleteAlias(aliasId: string): Promise<boolean> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/v1/aliases/${aliasId}`, {
    method: "DELETE",
    headers,
  });
  return res.ok;
}

export interface AgentMessageItem {
  role: string;
  name: string;
  content: string;
  timestamp: string;
}

export interface FrameworkTemplate {
  id: string;
  name: string;
  description: string;
  agents?: any[];
  nodes?: string[];
}

export interface FrameworkInfo {
  framework: string;
  is_installed: boolean;
  templates: FrameworkTemplate[];
}

export interface FrameworkRunResult {
  run_id: string;
  framework: string;
  template: string;
  status: string;
  task: string;
  agent_dialogue: AgentMessageItem[];
  final_output: string;
  execution_time_ms: number;
  metadata: Record<string, any>;
}

export async function fetchFrameworks(): Promise<FrameworkInfo[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/v1/frameworks`, { headers });
  if (!res.ok) return [];
  const json = await res.json();
  return json.data.frameworks || [];
}

export async function runFrameworkTask(
  framework: string,
  task: string,
  template?: string,
  config?: Record<string, any>
): Promise<FrameworkRunResult> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/v1/frameworks/${framework}/run`, {
    method: "POST",
    headers,
    body: JSON.stringify({ task, template, config }),
  });
  if (!res.ok) {
    const json = await res.json();
    throw new Error(json.detail || `Framework execution failed with ${res.status}`);
  }
  const json = await res.json();
  return json.data;
}

export async function fetchFrameworkRun(runId: string): Promise<FrameworkRunResult | null> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/v1/frameworks/runs/${runId}`, { headers });
  if (!res.ok) return null;
  const json = await res.json();
  return json.data;
}

export interface VoiceProfileData {
  profile_id: string;
  name: string;
  duration_sec: number;
  detected_pitch_hz: number;
  detected_rate_wpm: number;
  tonal_profile: string;
  pitch_adjustment: string;
  rate_adjustment: string;
  sample_filename: string;
  is_active: boolean;
}

export interface VoiceProfileResponse {
  has_profile: boolean;
  profile?: VoiceProfileData;
  active_voice: string;
  has_reference_audio: boolean;
}

export async function fetchVoiceProfile(): Promise<VoiceProfileResponse | null> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/v1/voice/clone/current`, { headers });
  if (!res.ok) return null;
  const json = await res.json();
  return json.data;
}

export async function uploadVoiceSample(
  audioBase64: string,
  filename = "reference.wav"
): Promise<VoiceProfileData> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/v1/voice/clone/upload`, {
    method: "POST",
    headers,
    body: JSON.stringify({ audio_base64: audioBase64, filename }),
  });
  if (!res.ok) {
    const json = await res.json();
    throw new Error(json.detail || "Failed to upload and analyze voice sample");
  }
  const json = await res.json();
  return json.data.profile;
}

export async function previewClonedVoice(text: string): Promise<string> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/v1/voice/clone/preview`, {
    method: "POST",
    headers,
    body: JSON.stringify({ text }),
  });
  if (!res.ok) {
    const json = await res.json();
    throw new Error(json.detail || "Failed to generate voice preview");
  }
  const json = await res.json();
  return json.data.audio_base64;
}

export async function activateClonedVoice(): Promise<boolean> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/v1/voice/clone/activate`, {
    method: "POST",
    headers,
  });
  return res.ok;
}





