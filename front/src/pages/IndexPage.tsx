import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createUser, createThread } from "@/api/cvScreenerClient";
import { ApiError } from "@/api/http";
import { saveSession } from "@/lib/storage";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

function getExistingUserFrom401(body: unknown): {
  user_id: number;
  name: string;
} | null {
  const detail =
    typeof body === "object" && body !== null && "detail" in body
      ? (body as { detail: unknown }).detail
      : null;
  if (
    typeof detail === "object" &&
    detail !== null &&
    "user_id" in detail &&
    typeof (detail as { user_id: unknown }).user_id === "number"
  ) {
    const d = detail as { user_id: number; name?: string | null };
    return {
      user_id: d.user_id,
      name: d.name ?? "",
    };
  }
  return null;
}

export default function IndexPage() {
  const [name, setName] = useState("");
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();

  const start = async () => {
    if (!name.trim()) {
      setStatus("Please enter a name first.");
      return;
    }

    setBusy(true);
    setStatus("Creating user...");
    try {
      let userId: number;
      let userName: string;

      try {
        const userRes = await createUser(name.trim());
        userId = userRes.user_id;
        userName = name.trim();
      } catch (e) {
        const existing =
          e instanceof ApiError && e.status === 401
            ? getExistingUserFrom401(e.body)
            : null;
        if (existing) {
          userId = existing.user_id;
          userName = existing.name || name.trim();
          setStatus("Existing user found. Creating thread...");
        } else {
          throw e;
        }
      }

      setStatus("Creating thread...");
      const threadRes = await createThread(userId);
      saveSession({
        userId: String(userId),
        userName,
        threadId: threadRes.thread_id,
      });

      setStatus("✅ Done. Entering chat...");
      navigate("/chat");
    } catch (e) {
      console.error(e);
      setStatus("❌ Error creating user/thread. Check the console (F12).");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl px-6 py-8 font-sans">
      <h1 className="mb-2 text-2xl font-semibold">CV Screener</h1>
      <p className="text-zinc-600">
        Enter your name to get started.
      </p>

      <div className="mt-6 flex gap-2">
        <Input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Username"
          className="flex-1"
        />
        <Button onClick={start} disabled={busy}>
          {busy ? "..." : "Start"}
        </Button>
      </div>

      <p className="mt-4 text-sm text-zinc-600">{status}</p>
    </div>
  );
}
