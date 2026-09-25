import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  base: '/app/',
  server: {
    port: 5173,
    proxy: {
      '/stocks': 'http://127.0.0.1:8000',
      '/candles': 'http://127.0.0.1:8000',
      '/scores': 'http://127.0.0.1:8000',
      '/detect': 'http://127.0.0.1:8000',
      '/alerts': 'http://127.0.0.1:8000',
      '/settings': 'http://127.0.0.1:8000',
      '/ingest': 'http://127.0.0.1:8000',
      '/replay': 'http://127.0.0.1:8000',
      '/quality': 'http://127.0.0.1:8000',
      '/health': 'http://127.0.0.1:8000',
      '/universe': 'http://127.0.0.1:8000',
    },
  },
});
