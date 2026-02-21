import { Routes, Route, Navigate } from "react-router-dom";
import IndexPage from "../pages/IndexPage";
import ChatPage from "../pages/ChatPage";

export default function AppRouter() {
  return (
    <Routes>
      <Route path="/" element={<IndexPage />} />
      <Route path="/chat" element={<ChatPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
