import type { ChatMessage } from "@/api/types";
import { ChatBubble } from "./ChatBubble";
import { ScrollArea } from "@/components/ui/scroll-area";

export interface ChatMessageListProps {
  messages: ChatMessage[];
  isSending: boolean;
}

export function ChatMessageList({ messages, isSending }: ChatMessageListProps) {
  return (
    <ScrollArea className="flex-1">
      <div className="mx-auto flex max-w-3xl flex-col gap-3 p-4">
        {messages.map((m) => (
          <ChatBubble
            key={m.id}
            message={m}
            isStreaming={m.role === "assistant" && isSending && !m.content}
          />
        ))}
      </div>
    </ScrollArea>
  );
}
