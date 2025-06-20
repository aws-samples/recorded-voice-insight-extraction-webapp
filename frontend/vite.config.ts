import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0', // Bind to all interfaces for VSCode port forwarding
    port: 3000,
    // No proxy needed - React app will call API Gateway directly
  }
});
