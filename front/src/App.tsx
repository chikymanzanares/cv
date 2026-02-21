import { useEffect, useState } from "react";

export default function App() {
  const [status, setStatus] = useState("cargando...");

  useEffect(() => {
    fetch("/api/openapi.json")
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then(() => setStatus("✅ conectó con la API via proxy"))
      .catch((e) => setStatus(`❌ error conectando con la API: ${String(e)}`));
  }, []);

  return (
    <div style={{ fontFamily: "system-ui", padding: 24 }}>
      <h1>Hola mundo 👋</h1>
      <p>Front en Docker funcionando.</p>
      <p>{status}</p>
    </div>
  );
}