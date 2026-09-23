// Qual domínio serve o quê (site.md §2.2, plano 5.0). Função pura: o `proxy.ts` só
// traduz a decisão em resposta, e os testes cobrem a decisão sem subir o Next.
//
// - `app.alpherion.com.br` serve só o app: `/` vira `/inicio` (que manda para a carteira
//   ou para a criação dela); o resto do site público é redirecionado para o domínio dele.
// - `alpherion.com.br` manda `/entrar`, `/cadastro` e `/carteira` para o app.
// - Em dev (`SITE_URL` = `APP_URL`) o mesmo host serve os dois, sem redirecionar.
// - Rota protegida sem cookie de sessão vai para `/entrar?next=`. É um filtro barato e
//   **otimista**: quem decide de verdade é `requireSession()` em cada página e rota.

/** Prefixos que só existem no app. */
export const APP_PREFIXES = ["/inicio", "/carteira", "/entrar", "/cadastro", "/conta"] as const;
/** Prefixos que exigem sessão. */
export const PROTECTED_PREFIXES = ["/inicio", "/carteira", "/conta"] as const;

const matches = (path: string, prefixes: readonly string[]) =>
  prefixes.some((p) => path === p || path.startsWith(`${p}/`));

export const isAppPath = (path: string) => matches(path, APP_PREFIXES);
export const isProtectedPath = (path: string) => matches(path, PROTECTED_PREFIXES);

export type RouteDecision =
  | { kind: "redirect"; url: string }
  | { kind: "rewrite"; path: string }
  | { kind: "next"; app: boolean };

export function decideRoute(input: {
  host: string | null;
  path: string;
  search: string;
  hasSessionCookie: boolean;
  siteUrl: string;
  appUrl: string;
}): RouteDecision {
  const site = new URL(input.siteUrl);
  const app = new URL(input.appUrl);
  const split = site.host !== app.host;
  const onApp = !split || input.host === app.host;
  const onSite = !split || input.host !== app.host;
  let path = input.path;

  if (split && onSite && !onApp && isAppPath(path)) {
    return { kind: "redirect", url: new URL(path + input.search, app).toString() };
  }
  if (split && onApp && !onSite && path !== "/" && !isAppPath(path)) {
    return { kind: "redirect", url: new URL(path + input.search, site).toString() };
  }
  if (path === "/cadastro" || path.startsWith("/cadastro/")) {
    return { kind: "redirect", url: new URL(`/entrar${input.search}`, app).toString() };
  }

  const rewriteRoot = split && onApp && path === "/";
  if (rewriteRoot) path = "/inicio";

  if (isProtectedPath(path) && !input.hasSessionCookie) {
    const login = new URL("/entrar", app);
    login.searchParams.set("next", (rewriteRoot ? "/inicio" : input.path) + input.search);
    return { kind: "redirect", url: login.toString() };
  }
  if (rewriteRoot) return { kind: "rewrite", path };
  return { kind: "next", app: isAppPath(path) };
}

/** CSP das rotas do app: script só com nonce (e o Umami, se houver). Estilo inline segue. */
export function appCsp(nonce: string, opts: { dev: boolean; analyticsOrigin?: string | null }): string {
  const analytics = opts.analyticsOrigin ? ` ${opts.analyticsOrigin}` : "";
  return [
    "default-src 'self'",
    `script-src 'self' 'nonce-${nonce}'${analytics}${opts.dev ? " 'unsafe-eval'" : ""}`,
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data:",
    "font-src 'self'",
    `connect-src 'self'${analytics}${opts.dev ? " ws: wss:" : ""}`,
    "frame-src 'none'",
    "object-src 'none'",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    // O login com Google é um POST para /api/entrar/google que redireciona ao provedor.
    "form-action 'self' https://accounts.google.com",
    ...(opts.dev ? [] : ["upgrade-insecure-requests"]),
  ].join("; ");
}
