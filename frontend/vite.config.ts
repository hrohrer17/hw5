import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The backend allows this origin (CORS), so keep the board on 5173.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, strictPort: true },
})
