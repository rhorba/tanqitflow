import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: '.',
  fullyParallel: false,
  forbidOnly: false,
  retries: 1,
  workers: 1,
  reporter: [['html', { outputFolder: 'artifacts/recording-report', open: 'never' }], ['list']],
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:4173',
    ignoreHTTPSErrors: true,
    video: { mode: 'on', size: { width: 1280, height: 720 } },
    screenshot: 'only-on-failure',
    trace: 'on-first-retry',
    viewport: { width: 1280, height: 720 },
    headless: false,
    actionTimeout: 30000,
    navigationTimeout: 30000,
  },
  timeout: 90000,
  outputDir: 'artifacts/recording-results',
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'], headless: false },
    },
  ],
  webServer: {
    // Run from frontend root using npm script
    command: 'npm run dev:recording',
    cwd: 'C:\\Users\\moham\\OneDrive - um5.ac.ma\\Desktop\\tanqitflow\\frontend',
    url: 'http://localhost:4173',
    reuseExistingServer: true,
    timeout: 60000,
    stdout: 'pipe',
    stderr: 'pipe',
  },
})
