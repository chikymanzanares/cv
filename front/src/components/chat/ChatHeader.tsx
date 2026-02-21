import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";

export interface ChatHeaderProps {
  userName: string;
  userId: string;
  threadId: string;
  status: string;
  onReset: () => void;
}

export function ChatHeader({
  userName,
  userId,
  threadId,
  status,
  onReset,
}: ChatHeaderProps) {
  return (
    <header className="shrink-0 px-4 py-4">
      <Separator className="absolute left-0 right-0 top-0" />
      <div className="mx-auto flex max-w-3xl justify-between gap-4">
        <div className="min-w-0">
          <p className="font-semibold">CV Screener Chat</p>
          <p className="text-xs text-zinc-500">
            User: {userName || "—"} (id: {userId || "—"}) · Thread: {threadId || "—"}
            {status && ` · ${status}`}
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={onReset} className="shrink-0">
          Reset
        </Button>
      </div>
    </header>
  );
}
