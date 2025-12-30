import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // Load env file based on mode (seedline, elevenup, or development)
  // This allows: npm run build --mode seedline or npm run build --mode elevenup
  const env = loadEnv(mode, process.cwd(), '')

  return {
    plugins: [react()],
    server: {
      port: 5173,
      strictPort: true, // Fail if port 5173 is busy instead of picking another port
      proxy: {
        // Proxy API requests to the Python backend
        '/api': {
          target: 'http://localhost:5050',
          changeOrigin: true,
          secure: false,
        }
      }
    }
  }
})
