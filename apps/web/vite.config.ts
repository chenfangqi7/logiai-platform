import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    proxy: {
      '/api': { target: process.env.VITE_API_PROXY_TARGET || 'http://localhost:8000', changeOrigin: true },
      '/health': { target: process.env.VITE_API_PROXY_TARGET || 'http://localhost:8000', changeOrigin: true },
    },
  },
})
