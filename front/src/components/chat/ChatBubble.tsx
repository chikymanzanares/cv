import { cn } from "@/lib/utils";
import type { ChatMessage as ChatMessageType } from "@/api/types";

export interface ChatBubbleProps {
  message: ChatMessageType;
  isStreaming?: boolean;
}

export function ChatBubble({ message, isStreaming }: ChatBubbleProps) {
  const isUser = message.role === "user";
  const hasSources = !isUser && Array.isArray(message.sources) && message.sources.length > 0;

  return (
    <div
      className={cn(
        "max-w-[80%] rounded-2xl border border-zinc-200 px-3 py-2.5 shadow-sm",
        isUser ? "ml-auto bg-zinc-100" : "bg-white"
      )}
    >
      <p className="mb-1 text-xs font-medium text-zinc-500">
        {isUser ? "You" : "Assistant"}
      </p>
      <div className="whitespace-pre-wrap text-sm">
        {message.content ||
          (message.role === "assistant" && isStreaming ? "…" : "")}
      </div>
      {hasSources && (
        <div className="mt-2 flex flex-wrap gap-1.5 border-t border-zinc-100 pt-2">
          <span className="text-xs text-zinc-400">Sources:</span>
          {message.sources!.map((cvId) => (
            <a
              key={cvId}
              href={`/cvs/${cvId}/cv.pdf`}
              target="_blank"
              rel="noopener noreferrer"
              className="rounded-full bg-zinc-100 px-2 py-0.5 text-xs font-medium text-zinc-600 hover:bg-zinc-200 hover:text-zinc-900 transition-colors"
            >
              {cvId}
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
