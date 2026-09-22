import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/socket.io': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        ws: true,
      },
    },
  },
  build: {
    // Never inline webfonts as data: URIs. Vite inlines assets under 4KB by
    // default, which swept up the small @fontsource subsets (Greek, Cyrillic,
    // Vietnamese) — that both trips `font-src 'self'` in our CSP and forces
    // every visitor to download subsets they will never render, defeating the
    // unicode-range lazy-loading those files exist for.
    assetsInlineLimit: (filePath: string) =>
      /\.(woff2?|ttf|otf|eot)$/i.test(filePath) ? false : undefined,
    rollupOptions: {
      output: {
        manualChunks: {
          react: ['react', 'react-dom', 'react-router-dom'],
          query: ['@tanstack/react-query'],
          ui: ['zustand', 'axios'],
        },
      },
    },
  },
})
