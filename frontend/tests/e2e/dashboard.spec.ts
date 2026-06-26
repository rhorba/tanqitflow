import { test, expect, Page } from "@playwright/test";

const VALID_EMAIL = process.env.E2E_ADMIN_EMAIL || "admin@demo.ma";
const VALID_PASS = process.env.E2E_ADMIN_PASS || "Demo1234!";

async function loginAndGo(page: Page, path: string) {
  await page.goto("/login");
  await page.getByLabel(/email/i).fill(VALID_EMAIL);
  await page.getByLabel(/password|mot de passe/i).fill(VALID_PASS);
  await page.getByRole("button", { name: /connexion|login|sign in/i }).click();
  await page.waitForURL((url) => !url.pathname.includes("/login"), { timeout: 10000 });
  if (path !== "/") {
    await page.goto(path);
  }
}

test.describe("Dashboard page", () => {
  test("KPI cards load and display numbers", async ({ page }) => {
    await loginAndGo(page, "/");
    // KPI cards should contain numeric values (SIV, NRW, flagged DMAs)
    await expect(page.locator("[data-testid='kpi-card'], .kpi-card, [class*='kpi']").first()).toBeVisible({
      timeout: 10000,
    });
  });

  test("trend chart renders", async ({ page }) => {
    await loginAndGo(page, "/");
    // Recharts renders an SVG
    const svg = page.locator("svg").first();
    await expect(svg).toBeVisible({ timeout: 10000 });
  });

  test("date range filter buttons exist", async ({ page }) => {
    await loginAndGo(page, "/");
    // Range selector: 1M / 3M / 6M / 12M
    const rangeButtons = page.getByRole("button", { name: /1M|3M|6M|12M/i });
    await expect(rangeButtons.first()).toBeVisible({ timeout: 10000 });
  });
});

test.describe("DMA list page", () => {
  test("table loads with column headers", async ({ page }) => {
    await loginAndGo(page, "/dmas");
    const table = page.getByRole("table").first();
    await expect(table).toBeVisible({ timeout: 10000 });
    // Should have at least one column header
    const headers = page.getByRole("columnheader");
    await expect(headers.first()).toBeVisible({ timeout: 5000 });
  });
});

test.describe("Worklist page", () => {
  test("worklist page loads", async ({ page }) => {
    await loginAndGo(page, "/worklist");
    await expect(page).toHaveURL(/\/worklist/);
    // Page renders without crashing
    await expect(page.getByRole("main").first()).toBeVisible({ timeout: 10000 });
  });
});
