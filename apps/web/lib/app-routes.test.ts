import { describe, expect, it } from "vitest";
import { appCsp, decideRoute } from "@/lib/app-routes";

const PROD = { siteUrl: "https://alpherion.com.br", appUrl: "https://app.alpherion.com.br" };
const DEV = { siteUrl: "http://localhost:3000", appUrl: "http://localhost:3000" };

const route = (
  urls: typeof PROD,
  host: string,
  path: string,
  { cookie = false, search = "" }: { cookie?: boolean; search?: string } = {},
) => decideRoute({ ...urls, host, path, search, hasSessionCookie: cookie });

describe("domínios do site e do app", () => {
  it("site público manda /entrar e /carteira para o app, com a query", () => {
    expect(route(PROD, "alpherion.com.br", "/entrar", { search: "?next=/carteira" })).toEqual({
      kind: "redirect",
      url: "https://app.alpherion.com.br/entrar?next=/carteira",
    });
    expect(route(PROD, "alpherion.com.br", "/carteira/importar/b3")).toEqual({
      kind: "redirect",
      url: "https://app.alpherion.com.br/carteira/importar/b3",
    });
  });

  it("/cadastro é o /entrar", () => {
    expect(route(PROD, "app.alpherion.com.br", "/cadastro")).toEqual({
      kind: "redirect",
      url: "https://app.alpherion.com.br/entrar",
    });
  });

  it("app não serve páginas do site: manda para o domínio público", () => {
    expect(route(PROD, "app.alpherion.com.br", "/acoes/petr4")).toEqual({
      kind: "redirect",
      url: "https://alpherion.com.br/acoes/petr4",
    });
  });

  it("o site público segue normal", () => {
    expect(route(PROD, "alpherion.com.br", "/acoes/petr4")).toEqual({ kind: "next", app: false });
    expect(route(PROD, "alpherion.com.br", "/")).toEqual({ kind: "next", app: false });
  });

  it("/ do app vira /inicio com sessão, e /entrar sem ela", () => {
    expect(route(PROD, "app.alpherion.com.br", "/", { cookie: true })).toEqual({ kind: "rewrite", path: "/inicio" });
    expect(route(PROD, "app.alpherion.com.br", "/")).toEqual({
      kind: "redirect",
      url: "https://app.alpherion.com.br/entrar?next=%2Finicio",
    });
  });

  it("rota protegida sem cookie vai para /entrar guardando o destino", () => {
    expect(route(PROD, "app.alpherion.com.br", "/carteira/proventos")).toEqual({
      kind: "redirect",
      url: "https://app.alpherion.com.br/entrar?next=%2Fcarteira%2Fproventos",
    });
    expect(route(PROD, "app.alpherion.com.br", "/carteira", { cookie: true })).toEqual({ kind: "next", app: true });
    expect(route(PROD, "app.alpherion.com.br", "/entrar")).toEqual({ kind: "next", app: true });
  });

  it("em dev o mesmo host serve os dois, sem redirecionar entre domínios", () => {
    expect(route(DEV, "localhost:3000", "/")).toEqual({ kind: "next", app: false });
    expect(route(DEV, "localhost:3000", "/acoes/petr4")).toEqual({ kind: "next", app: false });
    expect(route(DEV, "localhost:3000", "/carteira", { cookie: true })).toEqual({ kind: "next", app: true });
    expect(route(DEV, "localhost:3000", "/carteira")).toMatchObject({ kind: "redirect" });
  });

  it("prefixo parecido não conta como rota do app", () => {
    expect(route(PROD, "alpherion.com.br", "/carteiras-teoricas")).toEqual({ kind: "next", app: false });
  });
});

describe("CSP do app", () => {
  it("script só com nonce; sem unsafe-inline em script", () => {
    const csp = appCsp("abc", { dev: false, analyticsOrigin: "https://stats.alpherion.com.br" });
    const script = csp.split("; ").find((d) => d.startsWith("script-src"));
    expect(script).toBe("script-src 'self' 'nonce-abc' https://stats.alpherion.com.br");
    expect(csp).toContain("frame-ancestors 'none'");
    expect(csp).not.toContain("unsafe-eval");
  });
});
