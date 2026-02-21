import { useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { getSession, clearSession } from "../lib/storage";

export interface UseChatSessionResult {
  session: { userId: string; userName: string; threadId: string } | null;
  resetSession: () => void;
}

export function useChatSession(): UseChatSessionResult {
  const navigate = useNavigate();
  const session = useMemo(() => getSession(), []);

  useEffect(() => {
    if (!session?.userId || !session?.threadId || session.threadId === "undefined") {
      navigate("/", { replace: true });
    }
  }, [session?.userId, session?.threadId, navigate]);

  const resetSession = () => {
    clearSession();
    navigate("/", { replace: true });
  };

  return { session, resetSession };
}
