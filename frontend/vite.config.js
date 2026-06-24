import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],

  server: {
    port: 5173,
    proxy: {
      // Forward /api/* to the FastAPI backend during development
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },

  build: {
    // Use esbuild for fast, small production bundles
    minify: 'esbuild',
    // Skip source maps in production (reduces bundle size)
    sourcemap: false,
    // Raise the chunk size warning threshold (our vendor libs are fine)
    chunkSizeWarningLimit: 800,
    rollupOptions: {
      output: {
        // Split vendor code into a separate chunk for better CDN caching
        manualChunks: {
          vendor: ['react', 'react-dom', 'react-router-dom'],
          axios: ['axios'],
        },
      },
    },
  },
});
