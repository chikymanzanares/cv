import type { ChatMessage } from "../api/types";

export function addUserMessage(state: ChatMessage[], content: string): ChatMessage[] {
  return [
    ...state,
    { id: crypto.randomUUID(), role: "user", content },
  ];
}

export function addAssistantPlaceholder(state: ChatMessage[]): ChatMessage[] {
  return [
    ...state,
    { id: crypto.randomUUID(), role: "assistant", content: "" },
  ];
}

/** Use when you need the new assistant message id (e.g. for streaming). */
export function addAssistantPlaceholderWithId(
  state: ChatMessage[],
  assistantId: string
): ChatMessage[] {
  return [
    ...state,
    { id: assistantId, role: "assistant", content: "" },
  ];
}

export function appendAssistant(
  state: ChatMessage[],
  assistantId: string,
  chunk: string
): ChatMessage[] {
  return state.map((m) =>
    m.id === assistantId ? { ...m, content: m.content + chunk } : m
  );
}

export function finalizeAssistant(
  state: ChatMessage[],
  assistantId: string,
  fullText: string,
  sources?: string[]
): ChatMessage[] {
  return state.map((m) =>
    m.id === assistantId ? { ...m, content: fullText, sources } : m
  );
}

export function setAssistantError(
  state: ChatMessage[],
  assistantId: string,
  errorText: string
): ChatMessage[] {
  return state.map((m) =>
    m.id === assistantId ? { ...m, content: errorText } : m
  );
}
