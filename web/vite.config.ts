import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

const securityHeaders = { 'X-Content-Type-Options':'nosniff', 'Referrer-Policy':'no-referrer', 'X-Frame-Options':'DENY', 'Permissions-Policy':'microphone=(), camera=(), geolocation=()', 'Content-Security-Policy': "default-src 'self'; script-src 'self' https://apis.google.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: https://*.googleusercontent.com; connect-src 'self' http://127.0.0.1:8770 http://localhost:8770 ws://127.0.0.1:5173 ws://localhost:5173 https://*.googleapis.com; frame-src 'self' https://*.firebaseapp.com https://accounts.google.com; frame-ancestors 'none'; base-uri 'self'; object-src 'none'" };
export default defineConfig({
  plugins: [react()],
  server: { host: "127.0.0.1", port: 5173, headers: { ...securityHeaders, 'Content-Security-Policy': securityHeaders['Content-Security-Policy'].replace("script-src 'self'", "script-src 'self' 'unsafe-inline'") } },
  preview: { host: "127.0.0.1", port: 5173, headers: securityHeaders },
  resolve: { alias: { "@": path.resolve(import.meta.dirname, "./src") } },
  base: "/",
  build: { outDir: "dist" },
});
