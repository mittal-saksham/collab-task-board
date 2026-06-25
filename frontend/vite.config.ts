import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// Tailwind v4 plugs straight into Vite (no separate postcss/tailwind config file).
// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
})
