import path from "node:path";
import { loadEnvConfig } from "@next/env";
import createMDX from "@next/mdx";
import type { NextConfig } from "next";
import { APP_PREFIXES } from "./lib/app-routes";

// O `.env` fica na raiz do monorepo; em runtime quem carrega é lib/root-env.ts (via lib/env.ts).
// Aqui carregamos só para a CSP conhecer a origem do Umami em dev (em produção é o domínio fixo).
const isDev = process.env.NODE_ENV === "development";
if (isDev) loadEnvConfig(path.resolve(__dirname, "../.."), true);

// Headers de segurança (site.md §7.3). HSTS fica no nginx (depende do TLS) e o snippet do
// nginx NÃO deve repetir os headers abaixo — CSP duplicada é aplicada em interseção.
//
// CSP sem nonce no site público: nonce por request exige renderização dinâmica de toda
// página no Next, o que inviabiliza o SSG da landing e o ISR com cache de borda das páginas
// de ativo (§9). `'unsafe-inline'` cobre os scripts inline do próprio Next; o app autenticado
// (rotas dinâmicas) ganha CSP com nonce no `proxy.ts` e fica fora desta (`APP_ROUTES`).
const ANALYTICS_ORIGINS = new Set(["https://stats.alpherion.com.br"]);
if (isDev && process.env.UMAMI_SCRIPT_URL) ANALYTICS_ORIGINS.add(new URL(process.env.UMAMI_SCRIPT_URL).origin);
const analytics = [...ANALYTICS_ORIGINS].join(" ");

const csp = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline' ${analytics}${isDev ? " 'unsafe-eval'" : ""}`,
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: https://i.ytimg.com",
  "font-src 'self'",
  `connect-src 'self' ${analytics}${isDev ? " ws: wss:" : ""}`,
  "frame-src https://www.youtube-nocookie.com",
  "object-src 'none'",
  "frame-ancestors 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  ...(isDev ? [] : ["upgrade-insecure-requests"]),
].join("; ");

const securityHeaders = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=(), usb=()" },
  { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
  { key: "X-Frame-Options", value: "DENY" },
];

/** Prefixos do app, da mesma lista que o `proxy.ts` usa. */
const APP_ROUTES = APP_PREFIXES.map((p) => p.slice(1)).join("|");

const nextConfig: NextConfig = {
  output: "standalone",
  outputFileTracingRoot: path.resolve(__dirname, "../.."),
  poweredByHeader: false,
  reactStrictMode: true,
  pageExtensions: ["ts", "tsx", "mdx"],
  images: {
    formats: ["image/avif", "image/webp"],
  },
  async headers() {
    return [
      { source: "/(.*)", headers: securityHeaders },
      // As rotas do app recebem a CSP com nonce do proxy; duas CSPs valeriam em interseção.
      { source: `/((?!${APP_ROUTES}).*)`, headers: [{ key: "Content-Security-Policy", value: csp }] },
    ];
  },
};

// Textos legais em MDX com frontmatter (version, date) exportado como `frontmatter`.
// Plugins como string: exigência do Turbopack.
const withMDX = createMDX({
  options: {
    remarkPlugins: [["remark-gfm"], ["remark-frontmatter"], ["remark-mdx-frontmatter", { name: "frontmatter" }]],
  },
});

export default withMDX(nextConfig);
