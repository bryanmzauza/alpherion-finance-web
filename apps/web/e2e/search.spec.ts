import { expect, test } from "@playwright/test";

// Busca global do header (plano 4.1): o combobox só baixa no foco, e o teclado funciona
// mesmo com a API fora do ar (no CI não há API: a lista mostra o aviso e o "ver todos").

test("antes do foco não há lista; depois de digitar, há", async ({ page }) => {
  await page.goto("/");
  const input = page.getByRole("combobox").first();
  await expect(page.getByRole("listbox")).toHaveCount(0);
  await expect(input).toHaveAttribute("aria-expanded", "false");

  await input.focus();
  await input.fill("petr");
  await expect(page.getByRole("listbox").first()).toBeVisible();
  await expect(input).toHaveAttribute("aria-expanded", "true");
});

test("↓ marca uma opção pelo aria-activedescendant e Esc fecha", async ({ page }) => {
  await page.goto("/");
  const input = page.getByRole("combobox").first();
  await input.focus();
  await input.fill("petr");
  await expect(page.getByRole("option").last()).toBeVisible();

  await input.press("ArrowDown");
  const active = await input.getAttribute("aria-activedescendant");
  expect(active).toBeTruthy();
  await expect(page.locator(`[id="${active}"]`)).toHaveAttribute("aria-selected", "true");

  await input.press("Escape");
  await expect(input).toHaveAttribute("aria-expanded", "false");
});

test("Enter sem opção ativa vai para /busca?q=", async ({ page }) => {
  await page.goto("/");
  const input = page.getByRole("combobox").first();
  await input.focus();
  await input.fill("vale");
  await input.press("Enter");
  await expect(page).toHaveURL(/\/busca\?q=vale$/);
  await expect(page.getByRole("heading", { level: 1, name: "Busca" })).toBeVisible();
});

test("sem JavaScript, o formulário ainda leva à página de resultados", async ({ browser }) => {
  const context = await browser.newContext({ javaScriptEnabled: false });
  const page = await context.newPage();
  await page.goto("/");
  const input = page.getByRole("combobox").first();
  await input.fill("itub");
  await input.press("Enter");
  await expect(page).toHaveURL(/\/busca\?q=itub$/);
  await context.close();
});
