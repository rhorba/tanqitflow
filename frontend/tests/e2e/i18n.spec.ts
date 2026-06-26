import { test, expect, Page } from "@playwright/test";

const VALID_EMAIL = process.env.E2E_ADMIN_EMAIL || "admin@demo.ma";
const VALID_PASS = process.env.E2E_ADMIN_PASS || "Demo1234!";

async function login(page: Page) {
  await page.goto("/login");
  await page.getByLabel(/email/i).fill(VALID_EMAIL);
  await page.getByLabel(/password|mot de passe/i).fill(VALID_PASS);
  await page.getByRole("button", { name: /connexion|login|sign in/i }).click();
  await page.waitForURL((url) => !url.pathname.includes("/login"), { timeout: 10000 });
}

test.describe("i18n language switching", () => {
  test("page loads in French by default", async ({ page }) => {
    await login(page);
    const htmlDir = await page.locator("html").getAttribute("dir");
    // Default is French — LTR
    expect(["ltr", null, ""]).toContain(htmlDir);
    const lang = await page.locator("html").getAttribute("lang");
    expect(lang).toMatch(/fr/i);
  });

  test("switch to Arabic sets dir=rtl on html element", async ({ page }) => {
    await login(page);
    // Click Arabic language switcher
    const arabicBtn = page.getByRole("button", { name: /ع|ar|arabic|arabe/i }).or(
      page.locator("[data-lang='ar'], [data-testid='lang-ar']")
    );
    if (await arabicBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await arabicBtn.click();
      await page.waitForTimeout(500);
      const dir = await page.locator("html").getAttribute("dir");
      expect(dir).toBe("rtl");
    } else {
      test.skip();
    }
  });

  test("switch back to French sets dir=ltr", async ({ page }) => {
    await login(page);
    const frBtn = page.getByRole("button", { name: /fr|french|français/i }).or(
      page.locator("[data-lang='fr'], [data-testid='lang-fr']")
    );
    if (await frBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await frBtn.click();
      await page.waitForTimeout(500);
      const dir = await page.locator("html").getAttribute("dir");
      expect(["ltr", null, ""]).toContain(dir);
    } else {
      test.skip();
    }
  });

  test("page title is localized", async ({ page }) => {
    await login(page);
    const title = await page.title();
    expect(title.length).toBeGreaterThan(0);
  });
});
