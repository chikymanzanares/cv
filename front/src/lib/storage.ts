/**
 * Session storage in a single localStorage key.
 * Shape: { userId: string; userName: string; threadId: string }
 */

const SESSION_KEY = "cv_screener_session";

export interface Session {
  userId: string;
  userName: string;
  threadId: string;
}

export function getSession(): Session | null {
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    if (!raw) return null;
    const data = JSON.parse(raw) as unknown;
    if (
      typeof data === "object" &&
      data !== null &&
      "userId" in data &&
      "userName" in data &&
      "threadId" in data &&
      typeof (data as Session).userId === "string" &&
      typeof (data as Session).userName === "string" &&
      typeof (data as Session).threadId === "string"
    ) {
      return data as Session;
    }
    return null;
  } catch {
    return null;
  }
}

export function saveSession(session: Session): void {
  localStorage.setItem(SESSION_KEY, JSON.stringify(session));
}

export function clearSession(): void {
  localStorage.removeItem(SESSION_KEY);
}
