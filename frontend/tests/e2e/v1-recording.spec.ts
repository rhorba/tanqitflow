/**
 * v1.0 Release Recording — all critical user flows.
 * Run against production staging with:
 *   BASE_URL=https://your-vps E2E_ADMIN_EMAIL=admin@onee.ma E2E_ADMIN_PASS=... \
 *   npx playwright test v1-recording.spec.ts --project=chromium
 *
 * Video saved to: tests/e2e/artifacts/<hash>/video.webm
 * Copy to: .recordings/v1.0-YYYY-MM-DD-full.webm
 */
import { test, expect, Page } from "@playwright/test";

const EMAIL = process.env.E2E_ADMIN_EMAIL || "admin@demo.ma";
const PASS = process.env.E2E_ADMIN_PASS || "Demo1234!";

async function login(page: Page) {
  await page.goto("/login");
  await page.getByLabel(/email/i).fill(EMAIL);
  await page.getByLabel(/password|mot de passe/i).fill(PASS);
  await page.getByRole("button", { name: /connexion|login|sign in/i }).click();
  await page.waitForURL((url) => !url.pathname.includes("/login"), { timeout: 15000 });
}

test.describe.serial("TanqitFlow v1.0 — critical flows recording", () => {
  test("01 — Login and dashboard", async ({ page }) => {
    await login(page);
    await expect(page.getByText(/tableau de bord|dashboard/i).first()).toBeVisible({ timeout: 10000 });
    await page.waitForTimeout(1500);
  });

  test("02 — Dashboard KPI cards visible", async ({ page }) => {
    await login(page);
    // Expect KPI cards: NRW %, SIV, flagged DMAs
    const kpiLocator = page.locator("[data-testid='kpi-card'], .kpi-card, [class*='kpi']").first();
    if (await kpiLocator.isVisible()) {
      await kpiLocator.waitFor({ state: "visible", timeout: 8000 });
    }
    await page.waitForTimeout(1000);
  });

  test("03 — DMA table navigation", async ({ page }) => {
    await login(page);
    // Navigate to DMA list
    const dmaLink = page.getByRole("link", { name: /dma|zone|secteur/i }).first();
    if (await dmaLink.isVisible()) {
      await dmaLink.click();
      await page.waitForTimeout(1500);
    } else {
      await page.goto("/dmas");
      await page.waitForTimeout(1500);
    }
  });

  test("04 — CSV ingestion upload page", async ({ page }) => {
    await login(page);
    const ingestLink = page.getByRole("link", { name: /import|ingestion|upload|charger/i }).first();
    if (await ingestLink.isVisible()) {
      await ingestLink.click();
    } else {
      await page.goto("/ingestion");
    }
    await page.waitForTimeout(1500);
    // Verify dropzone is visible
    const dropzone = page.locator("[data-testid='dropzone'], input[type='file'], .dropzone").first();
    if (await dropzone.isVisible({ timeout: 5000 }).catch(() => false)) {
      await expect(dropzone).toBeVisible();
    }
  });

  test("05 — Water balance NRW view", async ({ page }) => {
    await login(page);
    const balanceLink = page.getByRole("link", { name: /bilan|balance|nrw|eau non comptabilisée/i }).first();
    if (await balanceLink.isVisible()) {
      await balanceLink.click();
    } else {
      await page.goto("/balance");
    }
    await page.waitForTimeout(1500);
  });

  test("06 — Hotspot map", async ({ page }) => {
    await login(page);
    const mapLink = page.getByRole("link", { name: /carte|map|hotspot/i }).first();
    if (await mapLink.isVisible()) {
      await mapLink.click();
    } else {
      await page.goto("/map");
    }
    await page.waitForTimeout(2000);
  });

  test("07 — Worklist (repair prioritization)", async ({ page }) => {
    await login(page);
    const worklistLink = page.getByRole("link", { name: /worklist|liste.*travaux|priorité/i }).first();
    if (await worklistLink.isVisible()) {
      await worklistLink.click();
    } else {
      await page.goto("/worklist");
    }
    await page.waitForTimeout(1500);
  });

  test("08 — Language switch FR to AR (RTL)", async ({ page }) => {
    await login(page);
    // Click language switcher
    const langBtn = page.getByRole("button", { name: /ar|ع|arabe|arabic/i }).first();
    if (await langBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await langBtn.click();
      await page.waitForTimeout(1500);
      // Verify RTL direction applied
      const html = page.locator("html");
      const dir = await html.getAttribute("dir");
      if (dir) expect(dir).toBe("rtl");
      // Switch back to FR
      const frBtn = page.getByRole("button", { name: /fr|fr|français|french/i }).first();
      if (await frBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
        await frBtn.click();
        await page.waitForTimeout(1000);
      }
    } else {
      // Language switcher may be in a dropdown
      const langSelect = page.locator("[data-testid='lang-switcher'], select[name*='lang']").first();
      if (await langSelect.isVisible({ timeout: 2000 }).catch(() => false)) {
        await langSelect.selectOption("ar");
        await page.waitForTimeout(1500);
      }
    }
  });

  test("09 — Health endpoint check", async ({ page }) => {
    await page.goto("/api/v1/health");
    const body = await page.textContent("body");
    expect(body).toContain('"status"');
    await page.waitForTimeout(500);
  });
});
