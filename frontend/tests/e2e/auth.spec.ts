import { test, expect } from "@playwright/test";

const VALID_EMAIL = process.env.E2E_ADMIN_EMAIL || "admin@demo.ma";
const VALID_PASS = process.env.E2E_ADMIN_PASS || "Demo1234!";

test.describe("Authentication flows", () => {
  test("login with valid credentials shows dashboard", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel(/email/i).fill(VALID_EMAIL);
    await page.getByLabel(/password|mot de passe/i).fill(VALID_PASS);
    await page.getByRole("button", { name: /connexion|login|sign in/i }).click();
    await expect(page).not.toHaveURL(/\/login/);
    await expect(page.getByText(/dashboard|tableau de bord/i).first()).toBeVisible({ timeout: 10000 });
  });

  test("login with invalid credentials shows error", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel(/email/i).fill("wrong@example.com");
    await page.getByLabel(/password|mot de passe/i).fill("WrongPassword1!");
    await page.getByRole("button", { name: /connexion|login|sign in/i }).click();
    await expect(page.getByText(/incorrect|invalide|invalid|401|erreur/i).first()).toBeVisible({
      timeout: 5000,
    });
    await expect(page).toHaveURL(/\/login/);
  });

  test("logout redirects to login page", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel(/email/i).fill(VALID_EMAIL);
    await page.getByLabel(/password|mot de passe/i).fill(VALID_PASS);
    await page.getByRole("button", { name: /connexion|login|sign in/i }).click();
    await page.waitForURL((url) => !url.pathname.includes("/login"), { timeout: 10000 });

    // Find and click logout
    const logoutBtn = page.getByRole("button", { name: /déconnexion|logout|sign out/i });
    if (await logoutBtn.isVisible()) {
      await logoutBtn.click();
    } else {
      // Try menu first
      await page.getByRole("button", { name: /menu|profil|profile/i }).first().click();
      await page.getByRole("menuitem", { name: /déconnexion|logout/i }).click();
    }
    await expect(page).toHaveURL(/\/login/, { timeout: 5000 });
  });
});
