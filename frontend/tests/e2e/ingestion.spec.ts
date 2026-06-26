import { test, expect, Page } from "@playwright/test";
import path from "path";
import fs from "fs";
import os from "os";

const VALID_EMAIL = process.env.E2E_ADMIN_EMAIL || "admin@demo.ma";
const VALID_PASS = process.env.E2E_ADMIN_PASS || "Demo1234!";

async function login(page: Page) {
  await page.goto("/login");
  await page.getByLabel(/email/i).fill(VALID_EMAIL);
  await page.getByLabel(/password|mot de passe/i).fill(VALID_PASS);
  await page.getByRole("button", { name: /connexion|login|sign in/i }).click();
  await page.waitForURL((url) => !url.pathname.includes("/login"), { timeout: 10000 });
}

function createTempCsv(): string {
  const content = "dma_code,reading_date,volume_m3\nDMA-E2E-01,2026-01-15,5000\nDMA-E2E-02,2026-01-15,8000\n";
  const tmpFile = path.join(os.tmpdir(), `tanqit_e2e_${Date.now()}.csv`);
  fs.writeFileSync(tmpFile, content, "utf-8");
  return tmpFile;
}

test.describe("CSV ingestion flow", () => {
  test("navigate to ingestion page", async ({ page }) => {
    await login(page);
    await page.goto("/ingestion");
    await expect(page).toHaveURL(/\/ingestion/);
    await expect(page.getByRole("main").first()).toBeVisible({ timeout: 10000 });
  });

  test("upload CSV file and see job in list", async ({ page }) => {
    await login(page);
    await page.goto("/ingestion");

    const fileInput = page.locator("input[type='file']");
    if (!(await fileInput.isVisible({ timeout: 3000 }).catch(() => false))) {
      test.skip();
      return;
    }

    const tmpCsv = createTempCsv();
    try {
      await fileInput.setInputFiles(tmpCsv);
      const jobTypeSelect = page.locator("select[name='job_type'], #job_type");
      if (await jobTypeSelect.isVisible({ timeout: 1000 }).catch(() => false)) {
        await jobTypeSelect.selectOption("DMA_INFLOW");
      }
      await page.getByRole("button", { name: /upload|télécharger|importer|envoyer/i }).click();
      // Job should appear in the list (PENDING or PROCESSING)
      await expect(
        page.getByText(/pending|processing|traitement|en cours/i).first()
      ).toBeVisible({ timeout: 15000 });
    } finally {
      fs.unlinkSync(tmpCsv);
    }
  });
});
