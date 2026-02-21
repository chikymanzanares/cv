import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";

export interface ChatComposerProps {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  disabled: boolean;
}

export function ChatComposer({
  value,
  onChange,
  onSend,
  disabled,
}: ChatComposerProps) {
  const onKeyDown: React.KeyboardEventHandler<HTMLInputElement> = (e) => {
    if (e.key === "Enter") onSend();
  };

  return (
    <footer className="shrink-0">
      <Separator />
      <div className="mx-auto flex max-w-3xl gap-2 p-4">
        <Input
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Type your question..."
          className="flex-1"
          disabled={disabled}
        />
        <Button onClick={onSend} disabled={disabled} className="shrink-0">
          {disabled ? "Sending..." : "Send"}
        </Button>
      </div>
    </footer>
  );
}
