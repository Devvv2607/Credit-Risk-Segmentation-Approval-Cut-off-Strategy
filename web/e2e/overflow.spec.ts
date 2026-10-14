import { expect, test } from "@playwright/test";
import path from "node:path";

const PAGES = ["/", "/analysis/", "/simulator/", "/scorecard/", "/methodology/", "/data/", "/reproducibility/", "/about/"];
const WIDTHS = [1440, 1024, 768, 375];
const SCREENSHOT_DIR = path.resolve(__dirname, "..", "..", "tests", "screenshots");

for (const width of WIDTHS) {
  test.describe(`viewport ${width}px`, () => {
    test.use({ viewport: { width, height: 900 } });

    for (const url of PAGES) {
      test(`no horizontal scroll on ${url}`, async ({ page }) => {
        await page.goto(url, { waitUntil: "networkidle" });
        // Let charts (ResponsiveContainer) measure and render.
        await page.waitForTimeout(400);
        const m = await page.evaluate(() => {
          const doc = document.documentElement;
          const cw = doc.clientWidth;
          // Report the outermost elements that stick out past the viewport, for debugging.
          const offenders: string[] = [];
          document.querySelectorAll("body *").forEach((el) => {
            const r = el.getBoundingClientRect();
            const p = el.parentElement?.getBoundingClientRect();
            if (r.width > 0 && r.right > cw + 1 && p && p.right <= cw + 1) {
              const cls = typeof el.className === "string" ? el.className : el.getAttribute("class") ?? "";
              offenders.push(`${el.tagName.toLowerCase()}.${cls.split(" ").slice(0, 4).join(".")} (right=${Math.round(r.right)})`);
            }
          });
          return { scrollWidth: doc.scrollWidth, clientWidth: cw, offenders: offenders.slice(0, 8) };
        });
        expect(m.scrollWidth, `overflowing elements: ${m.offenders.join(" | ")}`).toBeLessThanOrEqual(m.clientWidth);

        if (url === "/data/") {
          await page.screenshot({ path: path.join(SCREENSHOT_DIR, `data-sources-${width}.png`), fullPage: true });
        }
      });
    }
  });
}
