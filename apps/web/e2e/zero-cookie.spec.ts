import { expect, test, type Page } from "@playwright/test";

// Site público: **zero cookie** (site.md §8.5, plano 4.1). Nem cookie de sessão, nem de
// analytics, nem de preferência — e por isso não há banner. O teste confere as três
// portas por onde um cookie entra: `Set-Cookie` em qualquer resposta (página, RSC,
// route handler, estático), `document.cookie` e o jar do navegador.

const PAGES = ["/", "/mercado", "/acoes", "/fiis", "/agenda", "/setores", "/busca?q=petr", "/raio-x", "/nao-existe"];

function watchSetCookie(page: Page): string[] {
  const seen: string[] = [];
  page.on("response", async (response) => {
    const header = await response.headerValue("set-cookie").catch(() => null);
    if (header) seen.push(`${response.url()} → ${header}`);
  });
  return seen;
}

for (const path of PAGES) {
  test(`${path}: nenhum cookie`, async ({ page, context }) => {
    const setCookie = watchSetCookie(page);
    await page.goto(path, { waitUntil: "networkidle" });

    // Usar a busca do header também não pode gravar nada: carrega o módulo no foco e
    // chama o route handler `/api/market/search`.
    const search = page.getByRole("combobox").first();
    await search.focus();
    await search.fill("petr");
    await page.waitForLoadState("networkidle");

    expect(await page.evaluate(() => document.cookie)).toBe("");
    expect(await context.cookies()).toEqual([]);
    expect(setCookie).toEqual([]);
  });
}
