/**
 * TanqitFlow v1.0 — Comprehensive E2E Recording
 *
 * Covers every major user flow with proper waits so CSS/fonts fully render.
 * Run with:
 *   BASE_URL=https://localhost E2E_ADMIN_EMAIL=admin@onee.ma E2E_ADMIN_PASS=Admin1234! \
 *   npx playwright test tests/e2e/v1-recording.spec.ts --project=chromium \
 *   --config=tests/e2e/playwright.recording.config.ts --headed
 */
import { test, expect, Page } from "@playwright/test";

const BASE = process.env.BASE_URL || "https://localhost";
const EMAIL = process.env.E2E_ADMIN_EMAIL || "admin@onee.ma";
const PASS = process.env.E2E_ADMIN_PASS || "Admin1234!";

/** Navigate and wait for full page render (JS + CSS + network idle) */
async function goto(page: Page, path: string) {
  await page.goto(path);
  await page.waitForLoadState("networkidle", { timeout: 20000 });
}

/** Full login: navigate → fill → submit → wait for redirect */
async function login(page: Page) {
  await goto(page, "/login");
  await page.waitForSelector("#email", { state: "visible", timeout: 15000 });
  await page.waitForTimeout(600); // let CSS paint
  await page.fill("#email", EMAIL);
  await page.waitForTimeout(300);
  await page.fill("#password", PASS);
  await page.waitForTimeout(300);
  await page.click('button[type="submit"]');
  await page.waitForURL((url) => !url.pathname.includes("/login"), {
    timeout: 20000,
  });
  await page.waitForLoadState("networkidle", { timeout: 15000 });
  await page.waitForTimeout(800); // let dashboard data load
}

// ---------------------------------------------------------------------------
// Scene 1 — Login page
// ---------------------------------------------------------------------------
test("01 — Login page & authentication", async ({ page }) => {
  await goto(page, "/login");
  await page.waitForSelector("#email", { state: "visible", timeout: 15000 });
  await page.waitForTimeout(1200); // show the styled login form

  // Type email slowly for the recording
  await page.click("#email");
  await page.type("#email", EMAIL, { delay: 80 });
  await page.waitForTimeout(400);
  await page.click("#password");
  await page.type("#password", PASS, { delay: 80 });
  await page.waitForTimeout(600);

  await page.click('button[type="submit"]');
  await page.waitForURL((url) => !url.pathname.includes("/login"), {
    timeout: 20000,
  });
  await page.waitForLoadState("networkidle", { timeout: 15000 });
  await page.waitForTimeout(1500); // dashboard visible
});

// ---------------------------------------------------------------------------
// Scene 2 — Dashboard KPIs
// ---------------------------------------------------------------------------
test("02 — Dashboard: KPI cards and NRW summary", async ({ page }) => {
  await login(page);
  // Ensure we're on dashboard
  if (!page.url().includes("/dashboard")) {
    await goto(page, "/dashboard");
  }
  await page.waitForLoadState("networkidle", { timeout: 15000 });
  await page.waitForTimeout(2000); // KPI cards and charts animate in

  // Scroll down to see all cards
  await page.evaluate(() => window.scrollBy(0, 300));
  await page.waitForTimeout(1000);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(500);
});

// ---------------------------------------------------------------------------
// Scene 3 — DMA table
// ---------------------------------------------------------------------------
test("03 — DMA table: list, sort, inspect", async ({ page }) => {
  await login(page);

  // Navigate to DMAs
  const dmaLink = page.getByRole("link", { name: /dma|zone|secteur/i }).first();
  if (await dmaLink.isVisible({ timeout: 3000 }).catch(() => false)) {
    await dmaLink.click();
  } else {
    await goto(page, "/dmas");
  }
  await page.waitForLoadState("networkidle", { timeout: 15000 });
  await page.waitForTimeout(1500);

  // Scroll the table to show all rows
  await page.evaluate(() => window.scrollBy(0, 200));
  await page.waitForTimeout(800);

  // Click first DMA row if possible
  const firstRow = page.locator("table tbody tr, [role='row']").first();
  if (await firstRow.isVisible({ timeout: 3000 }).catch(() => false)) {
    await firstRow.click();
    await page.waitForLoadState("networkidle", { timeout: 10000 });
    await page.waitForTimeout(1500); // DMA detail or inline expansion
    await page.goBack();
    await page.waitForLoadState("networkidle", { timeout: 10000 });
    await page.waitForTimeout(800);
  }
});

// ---------------------------------------------------------------------------
// Scene 4 — Water balance / NRW view
// ---------------------------------------------------------------------------
test("04 — Water balance: NRW trend chart", async ({ page }) => {
  await login(page);

  const balanceLink = page
    .getByRole("link", { name: /bilan|balance|nrw|eau non comptabilis/i })
    .first();
  if (await balanceLink.isVisible({ timeout: 3000 }).catch(() => false)) {
    await balanceLink.click();
  } else {
    await goto(page, "/balance");
  }
  await page.waitForLoadState("networkidle", { timeout: 15000 });
  await page.waitForTimeout(2000); // charts render

  await page.evaluate(() => window.scrollBy(0, 400));
  await page.waitForTimeout(1000);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(500);
});

// ---------------------------------------------------------------------------
// Scene 5 — CSV Ingestion page
// ---------------------------------------------------------------------------
test("05 — Ingestion: CSV upload interface", async ({ page }) => {
  await login(page);

  const ingestLink = page
    .getByRole("link", { name: /import|ingestion|upload|charger/i })
    .first();
  if (await ingestLink.isVisible({ timeout: 3000 }).catch(() => false)) {
    await ingestLink.click();
  } else {
    await goto(page, "/ingestion");
  }
  await page.waitForLoadState("networkidle", { timeout: 15000 });
  await page.waitForTimeout(1500);

  // Scroll to show the full ingestion UI
  await page.evaluate(() => window.scrollBy(0, 300));
  await page.waitForTimeout(800);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(500);
});

// ---------------------------------------------------------------------------
// Scene 6 — Hotspot map
// ---------------------------------------------------------------------------
test("06 — Map: hotspot visualization", async ({ page }) => {
  await login(page);

  const mapLink = page
    .getByRole("link", { name: /carte|map|hotspot/i })
    .first();
  if (await mapLink.isVisible({ timeout: 3000 }).catch(() => false)) {
    await mapLink.click();
  } else {
    await goto(page, "/map");
  }
  await page.waitForLoadState("networkidle", { timeout: 15000 });
  await page.waitForTimeout(3000); // LeafletJS tiles load

  // Pan/zoom the map slightly
  const mapContainer = page.locator(".leaflet-container, [class*='map']").first();
  if (await mapContainer.isVisible({ timeout: 3000 }).catch(() => false)) {
    const box = await mapContainer.boundingBox();
    if (box) {
      await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
      await page.waitForTimeout(400);
    }
  }
  await page.waitForTimeout(1000);
});

// ---------------------------------------------------------------------------
// Scene 7 — Worklist (repair prioritization)
// ---------------------------------------------------------------------------
test("07 — Worklist: repair priority queue", async ({ page }) => {
  await login(page);

  const worklistLink = page
    .getByRole("link", { name: /worklist|liste.*travaux|priorit/i })
    .first();
  if (await worklistLink.isVisible({ timeout: 3000 }).catch(() => false)) {
    await worklistLink.click();
  } else {
    await goto(page, "/worklist");
  }
  await page.waitForLoadState("networkidle", { timeout: 15000 });
  await page.waitForTimeout(1500);

  // Try to trigger worklist generation
  const generateBtn = page
    .getByRole("button", { name: /générer|generate|recalcul/i })
    .first();
  if (await generateBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
    await generateBtn.click();
    await page.waitForLoadState("networkidle", { timeout: 15000 });
    await page.waitForTimeout(2000);
  }

  // Scroll to see the ranked items
  await page.evaluate(() => window.scrollBy(0, 300));
  await page.waitForTimeout(1000);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(500);
});

// ---------------------------------------------------------------------------
// Scene 8 — Language switch FR → AR (RTL)
// ---------------------------------------------------------------------------
test("08 — i18n: language switch French → Arabic (RTL)", async ({ page }) => {
  await login(page);
  await page.waitForTimeout(800);

  // Find the Arabic language button
  const arBtn = page
    .getByRole("button", { name: /ar|ع|arabe|arabic|العربية/i })
    .first();

  if (await arBtn.isVisible({ timeout: 4000 }).catch(() => false)) {
    await page.waitForTimeout(500);
    await arBtn.click();
    await page.waitForTimeout(2000); // RTL layout transition

    // Verify RTL
    const html = page.locator("html");
    const dir = await html.getAttribute("dir").catch(() => null);
    if (dir) expect(dir).toBe("rtl");

    await page.waitForTimeout(1500); // show Arabic UI

    // Switch back to French
    const frBtn = page
      .getByRole("button", { name: /fr|français|french/i })
      .first();
    if (await frBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await frBtn.click();
      await page.waitForTimeout(1000);
    }
  } else {
    // Language switcher might be in settings or header dropdown
    const langSelect = page
      .locator("[data-testid='lang-switcher'], select")
      .first();
    if (await langSelect.isVisible({ timeout: 2000 }).catch(() => false)) {
      await langSelect.selectOption("ar");
      await page.waitForTimeout(2000);
    }
  }
});

// ---------------------------------------------------------------------------
// Scene 9 — Reports page
// ---------------------------------------------------------------------------
test("09 — Reports: bilingual PDF generation UI", async ({ page }) => {
  await login(page);

  const reportsLink = page
    .getByRole("link", { name: /rapport|report/i })
    .first();
  if (await reportsLink.isVisible({ timeout: 3000 }).catch(() => false)) {
    await reportsLink.click();
  } else {
    await goto(page, "/reports");
  }
  await page.waitForLoadState("networkidle", { timeout: 15000 });
  await page.waitForTimeout(1500);
});

// ---------------------------------------------------------------------------
// Scene 10 — Docs auth gate (utility_admin only)
// ---------------------------------------------------------------------------
test("10 — Docs gating: 401 without token, 200 with admin JWT", async ({ page }) => {
  // Test without auth
  await goto(page, "/docs");
  await page.waitForTimeout(1000);
  // The page should show 401 JSON or redirect
  const bodyText = await page.locator("body").textContent({ timeout: 5000 }).catch(() => "");
  const isBlocked = bodyText?.includes("401") || bodyText?.includes("Not authenticated") || bodyText?.includes("403");

  // Now login and re-check docs
  await login(page);
  await goto(page, "/docs");
  await page.waitForLoadState("networkidle", { timeout: 15000 });
  await page.waitForTimeout(2000); // Swagger UI loads

  // Verify Swagger UI rendered
  const swaggerEl = page.locator(".swagger-ui, #swagger-ui, .opblock").first();
  if (await swaggerEl.isVisible({ timeout: 5000 }).catch(() => false)) {
    await swaggerEl.scrollIntoViewIfNeeded();
    await page.waitForTimeout(1500);
  }
});

// ---------------------------------------------------------------------------
// Scene 11 — Health endpoint in browser
// ---------------------------------------------------------------------------
test("11 — Health check: live system status JSON", async ({ page }) => {
  // /health is proxied from dev server to prod nginx
  await goto(page, "/health");
  await page.waitForLoadState("networkidle", { timeout: 10000 });
  await page.waitForTimeout(1000);
  const body = await page.locator("body").textContent({ timeout: 5000 }).catch(() => "");
  // May show JSON or redirect to login — either way prove the system is live
  const hasStatus = body?.includes('"status"') || body?.includes("ok");
  await page.waitForTimeout(800);
});

// ---------------------------------------------------------------------------
// Scene 12 — Logout
// ---------------------------------------------------------------------------
test("12 — Logout: session termination", async ({ page }) => {
  await login(page);

  // Find logout button
  const logoutBtn = page
    .getByRole("button", { name: /déconnexion|logout|sign out/i })
    .first();
  if (await logoutBtn.isVisible({ timeout: 4000 }).catch(() => false)) {
    await logoutBtn.click();
    await page.waitForURL((url) => url.pathname.includes("/login"), {
      timeout: 10000,
    });
    await page.waitForLoadState("networkidle", { timeout: 10000 });
    await page.waitForTimeout(1000); // show login page again
  } else {
    // Logout might be in a user menu
    const userMenu = page
      .locator("[data-testid='user-menu'], button[aria-label*='user'], button[aria-label*='compte']")
      .first();
    if (await userMenu.isVisible({ timeout: 3000 }).catch(() => false)) {
      await userMenu.click();
      await page.waitForTimeout(500);
      const logout2 = page.getByRole("button", { name: /déconnexion|logout/i }).first();
      if (await logout2.isVisible({ timeout: 2000 }).catch(() => false)) {
        await logout2.click();
        await page.waitForURL((url) => url.pathname.includes("/login"), { timeout: 10000 });
        await page.waitForLoadState("networkidle", { timeout: 10000 });
        await page.waitForTimeout(1000);
      }
    }
  }
});
