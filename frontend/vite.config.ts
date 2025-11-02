import path from "path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "src") },
  },
  server: {
    host: true,            // слушаем 0.0.0.0 внутри контейнера
    port: 5173,
    strictPort: true,
    // ВАЖНО: либо перечисление доменов, либо просто true.
    // Раз “Blocked request…”, даём true на dev.
    allowedHosts: true,

    // Vite HMR за обратным прокси с TLS (Caddy) — только WSS и 443
    hmr: {
      protocol: "wss",
      host: "rtk-smart-warehouse.ru", // домен, по которому заходим снаружи
      clientPort: 443,
      path: "/@vite",                 // дефолт, но укажем явно
    },

    // Если фронт ходит на /api того же домена — удобно прокинуть локально.
    proxy: {
      "/api": {
        target: "http://myapp-api:8000",
        changeOrigin: true,
        ws: true,
      },
    },

    // Иногда помогает, если браузер «ругается» на origin
    origin: "https://rtk-smart-warehouse.ru",
  },
});
