/**
 * Reusable SSE reader: fetch + ReadableStream, parse frames (blank-line separated),
 * extract event + data, dispatch via callback. No app-specific logic.
 */

export interface SSEEvent {
  event: string;
  data: string;
  id?: string;
}

export interface StreamSSEOptions {
  signal?: AbortSignal;
  headers?: Record<string, string>;
}

export async function streamSSE(
  url: string,
  onEvent: (evt: SSEEvent) => void,
  options: StreamSSEOptions = {}
): Promise<void> {
  const { signal, headers = {} } = options;

  const res = await fetch(url, {
    method: "GET",
    headers: { Accept: "text/event-stream", ...headers },
    signal,
  });

  if (!res.ok || !res.body) {
    throw new Error(`SSE request failed: ${res.status}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const frames = buffer.split("\n\n");
      buffer = frames.pop() ?? "";

      for (const frame of frames) {
        const lines = frame.split("\n").map((l) => l.trim());
        let eventName = "";
        let dataLine = "";
        let id: string | undefined;

        for (const line of lines) {
          if (line.startsWith("event:")) eventName = line.slice(6).trim();
          if (line.startsWith("data:")) dataLine += line.slice(5).trim();
          if (line.startsWith("id:")) id = line.slice(3).trim();
        }

        if (dataLine !== undefined) {
          onEvent({ event: eventName, data: dataLine, id });
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}
