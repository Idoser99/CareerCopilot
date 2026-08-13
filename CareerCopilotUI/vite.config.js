import { defineConfig } from "vite";
import { careerCopilotMock } from "./scripts/mockApiPlugin.js";

export default defineConfig({
  plugins: process.env.CAREER_COPILOT_MOCK === "true" ? [careerCopilotMock()] : [],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target:
          process.env.CAREER_COPILOT_API_TARGET || "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
