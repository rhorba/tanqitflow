/**
 * Vite config for E2E recording: serves frontend via HTTP (no SSL issues),
 * proxies API calls to the running Docker prod stack via https://localhost.
 */
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 4173,
    host: true,
    proxy: {
      // Forward /api/... to prod nginx WITHOUT path rewrite
      '/api': {
        target: 'https://localhost',
        changeOrigin: true,
        secure: false, // accept self-signed cert
      },
      // Forward /health to prod nginx
      '/health': {
        target: 'https://localhost',
        changeOrigin: true,
        secure: false,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
  },
})
