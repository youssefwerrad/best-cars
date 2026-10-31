import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Production assets are served by Django under /static/; `npm run dev` proxies the API to Django.
export default defineConfig(({ command }) => ({
  base: command === "build" ? "/static/" : "/",
  plugins: [react()],
  server: { proxy: { "/djangoapp": "http://localhost:8000" } },
}));
