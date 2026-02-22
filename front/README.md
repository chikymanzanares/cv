# Frontend — CV Screener Chat

React + Vite + Tailwind chat interface for the CV Screener. Streams LLM responses token-by-token via Server-Sent Events (SSE).

---

## Tech stack

- **React 18** + **TypeScript**
- **Vite 5** — dev server and bundler; proxy configured so `/api` and `/cvs` forward to `api:8000`
- **Tailwind CSS 4**
- **React Router DOM 6**
- **`components/ui/`** — UI primitives following the shadcn/ui pattern (`button`, `card`, `input`, `scroll-area`, `separator`)

---

## Folder structure

```
front/src/
  api/          HTTP client + typed API calls (cvScreenerClient.ts, types.ts)
  components/
    chat/       ChatBubble, ChatComposer, ChatHeader, ChatMessageList
    ui/         Shadcn-style primitives (button, input, card, …)
  hooks/        useChatSession, useRunStream (SSE streaming)
  lib/          chatReducer, sse.ts, storage.ts, utils.ts
  pages/        IndexPage (login), ChatPage (chat UI)
  router/       AppRouter (/ and /chat routes)
```

---

## Architecture notes

- **SSE streaming:** `useRunStream` consumes `GET /api/runs/{id}/events`, emitting tokens as they arrive so the assistant reply appears live.
- **Session:** `userId`, `userName`, and `threadId` are stored in `localStorage` and used to resume the chat.
- **Message state:** Reducer pattern in `chatReducer.ts` (add user/assistant message, append tokens, finalize, error).
- **Proxy:** Vite proxies `/api` and `/cvs` to the backend at `api:8000`, avoiding CORS when the front runs on port 5173.

---

## Commands

```bash
npm run dev      # Development server (http://localhost:5173)
npm run build    # TypeScript check + production build
npm run preview  # Serve production build locally
```

When running via Docker Compose, the front container uses `npm run dev` and the proxy target is the `api` service.
