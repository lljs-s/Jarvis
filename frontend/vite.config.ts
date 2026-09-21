// defineConfig aus vitest/config, damit der test-Abschnitt mitgeprueft wird.
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Der Vite-Server liefert im Entwicklungsbetrieb die Oberflaeche aus und
// reicht /api und /ws an den Python-Server weiter. Dadurch sprechen beide
// Seiten im Browser dieselbe Adresse - das vermeidet CORS-Sonderfaelle.
const jarvisPort = process.env.VITE_JARVIS_PORT ?? "8765";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": { target: `http://127.0.0.1:${jarvisPort}`, changeOrigin: false },
      "/ws": { target: `ws://127.0.0.1:${jarvisPort}`, ws: true, changeOrigin: false },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test-setup.ts"],
    css: false,
  },
});
