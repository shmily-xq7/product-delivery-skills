import { defineConfig } from 'vite'
import { fileURLToPath } from 'node:url'
export default defineConfig({
  esbuild: { jsx: "automatic" },
  resolve: { dedupe: ['react', 'react-dom'], alias: { react: fileURLToPath(new URL('./node_modules/react', import.meta.url)), 'react-dom': fileURLToPath(new URL('./node_modules/react-dom', import.meta.url)), antd: fileURLToPath(new URL('./node_modules/antd', import.meta.url)), 'react-router-dom': fileURLToPath(new URL('./node_modules/react-router-dom', import.meta.url)) } },
  server: { fs: { allow: [fileURLToPath(new URL('../../../..', import.meta.url))] } },
})
