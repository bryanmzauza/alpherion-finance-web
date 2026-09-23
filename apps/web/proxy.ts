import { getSessionCookie } from "better-auth/cookies";
import { NextResponse, type NextRequest } from "next/server";
import { appCsp, decideRoute } from "@/lib/app-routes";

// Proxy do Next 16 (antigo middleware): domínio certo, filtro otimista de sessão e CSP
// com nonce nas rotas do app (site.md §7.3). A decisão está em `lib/app-routes.ts`.
//
// Lê `process.env` direto, e não `lib/env`: o proxy roda separado do código de render e
// não deve carregar o `.env` da raiz nem validar o schema inteiro a cada request.

const SITE_URL = process.env.SITE_URL ?? "http://localhost:3000";
const APP_URL = process.env.APP_URL ?? SITE_URL;
const DEV = process.env.NODE_ENV === "development";
const ANALYTICS = process.env.UMAMI_SCRIPT_URL ? new URL(process.env.UMAMI_SCRIPT_URL).origin : null;

export function proxy(request: NextRequest) {
  const url = request.nextUrl;
  const decision = decideRoute({
    host: request.headers.get("host"),
    path: url.pathname,
    search: url.search,
    hasSessionCookie: Boolean(getSessionCookie(request)),
    siteUrl: SITE_URL,
    appUrl: APP_URL,
  });

  if (decision.kind === "redirect") return NextResponse.redirect(decision.url, 307);

  const isApp = decision.kind === "rewrite" || decision.app;
  if (!isApp) return NextResponse.next();

  // Rota do app: nonce novo por request; o Next o lê do header da requisição e o aplica
  // aos próprios scripts. As páginas do app já são dinâmicas (leem a sessão).
  const nonce = Buffer.from(crypto.randomUUID()).toString("base64");
  const csp = appCsp(nonce, { dev: DEV, analyticsOrigin: ANALYTICS });
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("x-nonce", nonce);
  requestHeaders.set("Content-Security-Policy", csp);

  const response =
    decision.kind === "rewrite"
      ? NextResponse.rewrite(new URL(decision.path, url), { request: { headers: requestHeaders } })
      : NextResponse.next({ request: { headers: requestHeaders } });
  response.headers.set("Content-Security-Policy", csp);
  response.headers.set("Cache-Control", "private, no-store");
  response.headers.set("X-Robots-Tag", "noindex");
  return response;
}

export const config = {
  matcher: [
    {
      // Fora: rotas de API (cada uma confere a própria sessão), estáticos e prefetch.
      source: "/((?!api|_next/static|_next/image|favicon.ico|brand|fonts|.*\\.[a-z0-9]+$).*)",
      missing: [
        { type: "header", key: "next-router-prefetch" },
        { type: "header", key: "purpose", value: "prefetch" },
      ],
    },
  ],
};
