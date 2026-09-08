import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    proxy: {
      '/upload': 'http://localhost:8000',
      '/query':  'http://localhost:8000',
      '/pdf':    'http://localhost:8000',
      '/pages':  'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
  optimizeDeps: {
    include: ['pdfjs-dist'],
  },
});
