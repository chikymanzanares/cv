/**
 * CV Screener API client: users, threads, postMessage (returns run_id).
 * SSE streaming is handled via lib/sse + useRunStream.
 */

import { fetchJson } from "./http";
import type {
  CreateUserRequest,
  CreateUserResponse,
  CreateThreadRequest,
  CreateThreadResponse,
  PostMessageRequest,
  PostMessageResponse,
  ThreadResponse,
  RunResponse,
} from "./types";

const API = "/api";

export async function createUser(name: string): Promise<CreateUserResponse> {
  const body: CreateUserRequest = { name };
  return fetchJson<CreateUserResponse>(`${API}/users`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function createThread(userId: number): Promise<CreateThreadResponse> {
  const body: CreateThreadRequest = { user_id: userId };
  return fetchJson<CreateThreadResponse>(`${API}/threads`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function postMessage(
  threadId: string,
  content: string
): Promise<PostMessageResponse> {
  const body: PostMessageRequest = { content };
  const res = await fetchJson<PostMessageResponse>(
    `${API}/threads/${encodeURIComponent(threadId)}/messages`,
    {
      method: "POST",
      body: JSON.stringify(body),
    }
  );
  if (typeof res.run_id !== "string") {
    throw new Error("run_id missing from PostMessage response");
  }
  return res;
}

export async function getThread(threadId: string): Promise<ThreadResponse> {
  return fetchJson<ThreadResponse>(
    `${API}/threads/${encodeURIComponent(threadId)}`
  );
}

export async function getRun(runId: string): Promise<RunResponse> {
  return fetchJson<RunResponse>(`${API}/runs/${encodeURIComponent(runId)}`);
}
