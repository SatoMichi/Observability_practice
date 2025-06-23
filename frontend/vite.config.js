import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true
  },
  css: {
    preprocessorOptions: {
      scss: {
        // 将来のSASS非推奨機能を無効化
        silenceDeprecations: ['legacy-js-api', 'import']
      }
    }
  }
}) 
