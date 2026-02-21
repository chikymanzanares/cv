/**
 * API request/response types matching the backend OpenAPI schema.
 * Use these for typed API calls; export ChatMessage/ChatRole for UI.
 */

// ─── Users ─────────────────────────────────────────────────────────────────
export interface CreateUserRequest {
  name: string;
}

export interface CreateUserResponse {
  user_id: number;
  name: string | null;
}

// ─── Threads ────────────────────────────────────────────────────────────────
export interface CreateThreadRequest {
  user_id: number;
}

export interface CreateThreadResponse {
  thread_id: string;
}

export interface ThreadMessageResponse {
  id: string;
  role: string;
  content: string;
  created_at: string;
}

export interface ThreadResponse {
  thread_id: string;
  user_id: number;
  messages: ThreadMessageResponse[];
}

// ─── Messages (post message → creates run) ──────────────────────────────────
export interface PostMessageRequest {
  content: string;
}

export interface PostMessageResponse {
  run_id: string;
}

// ─── Runs ──────────────────────────────────────────────────────────────────
export interface RunResponse {
  run_id: string;
  thread_id: string;
  status: string;
  created_at: string | null;
  started_at: string | null;
  finished_at: string | null;
  error: string | null;
}

// ─── UI types (shared) ─────────────────────────────────────────────────────
export type ChatRole = "user" | "assistant" | "system";

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
}
