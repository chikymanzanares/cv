import { useCallback, useRef } from "react";
import { streamSSE } from "../lib/sse";

export interface UseRunStreamCallbacks {
  onToken?: (text: string) => void;
  onFinal?: (text: string) => void;
  onDone?: () => void;
  onToolEvent?: (evt: { tool?: string; input?: unknown; output?: unknown }) => void;
}

function safeJsonParse<T = unknown>(s: string): T | null {
  try {
    return JSON.parse(s) as T;
  } catch {
    return null;
  }
}

export function useRunStream() {
  const abortRef = useRef<AbortController | null>(null);

  const start = useCallback(
    (runId: string, callbacks: UseRunStreamCallbacks) => {
      if (abortRef.current) {
        abortRef.current.abort();
      }
      const controller = new AbortController();
      abortRef.current = controller;

      const url = `/api/runs/${encodeURIComponent(runId)}/events`;

      streamSSE(
        url,
        (evt) => {
          const payload = safeJsonParse<Record<string, unknown>>(evt.data);
          if (evt.event === "token") {
            const text = (payload?.text as string) ?? "";
            callbacks.onToken?.(text);
          } else if (evt.event === "final") {
            const text = (payload?.text as string) ?? "";
            callbacks.onFinal?.(text);
          } else if (evt.event === "done") {
            callbacks.onDone?.();
          } else if (evt.event === "tool_start" || evt.event === "tool_end") {
            callbacks.onToolEvent?.({
              tool: payload?.tool as string,
              input: payload?.input,
              output: payload?.output,
            });
          }
        },
        { signal: controller.signal }
      ).catch((err) => {
        if (err?.name === "AbortError") return;
        callbacks.onDone?.();
      });
    },
    []
  );

  const cancel = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
  }, []);

  return { start, cancel };
}
