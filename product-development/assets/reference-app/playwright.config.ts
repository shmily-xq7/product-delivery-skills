import { defineConfig } from '@playwright/test'
export default defineConfig({ testDir: './tests', workers: 1, retries: 0, use: { baseURL: 'http://127.0.0.1:4179', headless: true, channel: process.env.PLAYWRIGHT_CHANNEL }, webServer: { command: 'npm run dev -- --port 4179 --strictPort', url: 'http://127.0.0.1:4179', reuseExistingServer: false } })
