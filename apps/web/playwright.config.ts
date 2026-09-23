import { defineConfig, devices } from "@playwright/test";

// Testes de navegador (plano 4.1): zero cookie no site público e a busca do header.
// Rodam contra o build de produção (`next start`), que é o que vai ao ar — o `next dev`
// tem comportamento de cache e de JS diferente.
//
// Local: `pnpm build && pnpm e2e` (usa o Edge/Chrome instalado via PW_CHANNEL, sem baixar
// navegador). CI: `playwright install chromium` e o Chromium do próprio Playwright.

const PORT = Number(process.env.E2E_PORT ?? 3100);

export default defineConfig({
  testDir: "e2e",
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["github"], ["list"]] : "list",
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    ...devices["Desktop Chrome"],
    ...(process.env.PW_CHANNEL ? { channel: process.env.PW_CHANNEL } : {}),
  },
  webServer: {
    command: `pnpm exec next start -p ${PORT}`,
    url: `http://127.0.0.1:${PORT}/robots.txt`,
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});
