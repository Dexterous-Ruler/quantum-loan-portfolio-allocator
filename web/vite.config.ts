import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// `allowedHosts` lets the dev/preview server answer a Cloudflare quick tunnel
// (`cloudflared tunnel --url http://localhost:4173`). The leading dot allows any
// subdomain, so the demo keeps working when the tunnel hands out a new hostname.
// Vercel serves `dist/` as static files and never runs this server, so this does
// not widen anything in production.
const TUNNEL_HOSTS = [".trycloudflare.com", ".loca.lt", ".ngrok-free.app", ".ngrok.io"];

export default defineConfig({
  plugins: [react()],
  build: { outDir: "dist", sourcemap: false },
  preview: { allowedHosts: TUNNEL_HOSTS },
  server: { allowedHosts: TUNNEL_HOSTS },
});
