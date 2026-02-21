import { cn } from "@/lib/utils";
import type { ChatMessage as ChatMessageType } from "@/api/types";

export interface ChatBubbleProps {
  message: ChatMessageType;
  isStreaming?: boolean;
}

export function ChatBubble({ message, isStreaming }: ChatBubbleProps) {
  const isUser = message.role === "user";
  return (
    <div
      className={cn(
        "max-w-[80%] rounded-2xl border border-zinc-200 px-3 py-2.5 shadow-sm",
        isUser
          ? "ml-auto bg-zinc-100"
          : "bg-white"
      )}
    >
      <p className="mb-1 text-xs font-medium text-zinc-500">
        {isUser ? "You" : "Assistant"}
      </p>
      <div className="whitespace-pre-wrap text-sm">
        {message.content ||
          (message.role === "assistant" && isStreaming ? "…" : "")}
      </div>
    </div>
  );
}
