import { useState, useEffect } from "react";
import type { ChatMessage, ChatRole } from "@/api/types";
import { useChatSession } from "@/hooks/useChatSession";
import { useRunStream } from "@/hooks/useRunStream";
import { getThread, postMessage } from "@/api/cvScreenerClient";
import {
  addUserMessage,
  addAssistantPlaceholderWithId,
  appendAssistant,
  finalizeAssistant,
  setAssistantError,
} from "@/lib/chatReducer";
import { ChatHeader } from "@/components/chat/ChatHeader";
import { ChatMessageList } from "@/components/chat/ChatMessageList";
import { ChatComposer } from "@/components/chat/ChatComposer";

const WELCOME: ChatMessage = {
  id: "welcome",
  role: "assistant",
  content:
    "Hi 👋 I'm your CV Screener. Ask me things like: “Who has experience with Python?”",
};

export default function ChatPage() {
  const { session, resetSession } = useChatSession();
  const runStream = useRunStream();

  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME]);
  const [input, setInput] = useState("");
  const [status, setStatus] = useState("");
  const [isSending, setIsSending] = useState(false);

  useEffect(() => {
    if (!session?.threadId || session.threadId === "undefined") return;

    let cancelled = false;

    (async () => {
      try {
        const thread = await getThread(session.threadId);
        const dbMessages = Array.isArray(thread?.messages) ? thread.messages : [];

        const mapped: ChatMessage[] = dbMessages.map((m) => ({
          id: String(m.id ?? crypto.randomUUID()),
          role: (m.role as ChatRole) ?? "system",
          content: String(m.content ?? ""),
        }));

        if (cancelled) return;

        setMessages((prev) => {
          const welcome = prev.find((x) => x.id === "welcome") ?? WELCOME;
          if (mapped.length === 0) return [welcome];
          return [welcome, ...mapped];
        });
      } catch (e) {
        console.error("Failed to load thread messages:", e);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [session?.threadId]);

  const send = async () => {
    const text = input.trim();
    if (!text || !session?.threadId || isSending) return;

    setIsSending(true);
    setStatus("Sending...");

    const assistantId = crypto.randomUUID();
    setMessages((prev) =>
      addAssistantPlaceholderWithId(addUserMessage(prev, text), assistantId)
    );
    setInput("");

    try {
      const { run_id } = await postMessage(session.threadId, text);
      setStatus("Streaming...");

      runStream.start(run_id, {
        onToken: (chunk) => {
          setMessages((prev) => appendAssistant(prev, assistantId, chunk));
        },
        onFinal: (fullText, sources) => {
          setMessages((prev) => finalizeAssistant(prev, assistantId, fullText, sources));
        },
        onDone: () => {
          setIsSending(false);
          setStatus("");
        },
      });
    } catch (e) {
      console.error(e);
      setMessages((prev) =>
        setAssistantError(
          prev,
          assistantId,
          "Streaming failed. Check backend SSE logs."
        )
      );
      setIsSending(false);
      setStatus("");
    }
  };

  if (!session) return null;

  return (
    <div className="flex h-dvh flex-col font-sans">
      <ChatHeader
        userName={session.userName}
        userId={session.userId}
        threadId={session.threadId}
        status={status}
        onReset={resetSession}
      />
      <main className="flex min-h-0 flex-1 flex-col">
        <ChatMessageList messages={messages} isSending={isSending} />
      </main>
      <ChatComposer
        value={input}
        onChange={setInput}
        onSend={send}
        disabled={isSending}
      />
    </div>
  );
}
