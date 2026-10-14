import { defineConfig } from "@playwright/test";

// Layout checks run against the static export in out/ (run `npm run build` first).
// Uses the locally installed Chrome by default; set PW_CHANNEL="" to use Playwright's
// bundled Chromium instead (after `npx playwright install chromium`).
const channel = process.env.PW_CHANNEL ?? "chrome";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: "http://127.0.0.1:4173",
    ...(channel ? { channel } : {}),
  },
  webServer: {
    command: "node scripts/serve-out.mjs",
    url: "http://127.0.0.1:4173/",
    reuseExistingServer: true,
    timeout: 30_000,
  },
});
