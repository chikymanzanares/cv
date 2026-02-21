import { useEffect, useState } from "react";

export default function App() {
  const [name, setName] = useState("");
  const [userId, setUserId] = useState<number | null>(null);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [status, setStatus] = useState("");

  useEffect(() => {
    const storedUserId = localStorage.getItem("user_id");
    const storedThreadId = localStorage.getItem("thread_id");
  
    if (!storedUserId) return;
  
    const uid = Number(storedUserId);
    setUserId(uid);
    setStatus("usuario recuperado");
  
    if (!storedThreadId) {
      loadOrCreateThread(uid);
      return;
    }
  
    fetch(`/api/threads/${storedThreadId}`)
      .then((res) => {
        if (!res.ok) throw new Error("thread no existe");
        return res.json();
      })
      .then((data) => {
        setThreadId(storedThreadId);
        setStatus("thread recuperado");
        console.log("mensajes:", data);
      })
      .catch(async () => {
        // si el thread guardado ya no existe → crea uno nuevo
        await loadOrCreateThread(uid);
      });
  }, []);

  const createUser = async () => {
    try {
      setStatus("creando usuario...");

      const res = await fetch("/api/users", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ name }),
      });

      if (!res.ok) throw new Error("error creando usuario");

      const data = await res.json();

      localStorage.setItem("user_id", data.user_id);
      setUserId(data.user_id);
      setStatus("✅ usuario creado");

      await loadOrCreateThread(data.user_id);
    } catch (e) {
      console.error(e);
      setStatus("❌ error creando usuario");
    }
  };

  const loadOrCreateThread = async (userId: number) => {
    const storedThreadId = localStorage.getItem("thread_id");

    if (storedThreadId) {
      setThreadId(storedThreadId);
      setStatus("thread recuperado");
      return;
    }

    try {
      setStatus("creando thread...");

      const res = await fetch("/api/threads", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ user_id: userId }),
      });

      if (!res.ok) throw new Error("error creando thread");

      const data = await res.json();

      localStorage.setItem("thread_id", data.id);
      setThreadId(data.id);
      setStatus("✅ thread creado");
    } catch (e) {
      console.error(e);
      setStatus("❌ error creando thread");
    }
  };

  return (
    <div style={{ fontFamily: "system-ui", padding: 24 }}>
      <h1>CV Screener Chat</h1>

      {!userId && (
        <>
          <input
            placeholder="Nombre de usuario"
            value={name}
            onChange={(e) => setName(e.target.value)}
            style={{ padding: 8, marginRight: 8 }}
          />
          <button onClick={createUser} style={{ padding: 8 }}>
            Crear Usuario
          </button>
        </>
      )}

      {userId && (
        <>
          <p>👤 Usuario ID: {userId}</p>
          {threadId && <p>💬 Thread ID: {threadId}</p>}
        </>
      )}

      <p>{status}</p>
    </div>
  );
}