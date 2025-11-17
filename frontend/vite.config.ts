import path from "path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  cacheDir: "node_modules/.vite",
  plugins: [
    react({
      fastRefresh: true,
    }),
  ],
  resolve: {
    alias: { "@": path.resolve(__dirname, "src") },
  },
  server: {
    host: true,
    port: 5173,
    strictPort: true,
    allowedHosts: true,
    hmr: {
      protocol: "wss",
      host: "rtk-smart-warehouse.ru",
      clientPort: 443,
      path: "/@vite",
      overlay: false,
    },
    watch: {
      ignored: [
        "**/index.html",
        "**/dist/**",
        "**/.git/**",
        "**/node_modules/**",
        "src/**/tailwind.css",
        "src/**/generated.css",
      ],
    },
    proxy: {
      "/api": {
        target: "http://myapp-api:8000",
        changeOrigin: true,
        ws: true,
      },
    },
    origin: "https://rtk-smart-warehouse.ru",
  },
});
