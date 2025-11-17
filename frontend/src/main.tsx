// 🔹 1. Импортируем "фикс" ДО всего остального
import "./hmr-keep-state";

// 🔹 2. Импортируем React и приложение
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./app/App.tsx";

// 🔹 3. Монтируем React как обычно
createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
