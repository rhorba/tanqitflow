import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: [["html", { outputFolder: "tests/e2e/artifacts/report" }], ["list"]],
  use: {
    baseURL: process.env.BASE_URL || "http://localhost:5173",
    video: "on",
    screenshot: "only-on-failure",
    trace: "on-first-retry",
  },
  outputDir: "tests/e2e/artifacts",
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: process.env.CI
    ? undefined
    : {
        command: "npm run dev",
        url: "http://localhost:5173",
        reuseExistingServer: !process.env.CI,
      },
});
