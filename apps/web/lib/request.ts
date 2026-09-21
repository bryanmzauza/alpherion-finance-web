import { env } from "@/lib/env";

// Helpers de request para route handlers (site.md §7.2 real_ip, §7.4 CSRF).

/** IP do cliente atrás da Cloudflare + nginx. Nunca confiar só no x-forwarded-for. */
export function clientIp(headers: Headers): string {
  return (
    headers.get("cf-connecting-ip") ??
    headers.get("x-real-ip") ??
    headers.get("x-forwarded-for")?.split(",")[0]?.trim() ??
    "0.0.0.0"
  );
}

/**
 * CSRF em route handlers mutáveis: o Origin (ou Sec-Fetch-Site) tem que ser o próprio site.
 * O Next faz isso nas server actions; route handlers precisam checar à mão (§7.4).
 */
export function isSameOrigin(headers: Headers): boolean {
  const fetchSite = headers.get("sec-fetch-site");
  if (fetchSite && fetchSite !== "same-origin" && fetchSite !== "none") return false;
  const origin = headers.get("origin");
  if (!origin) return fetchSite === "same-origin";
  const allowed = new Set([env.SITE_URL, env.APP_URL].map((u) => new URL(u).origin));
  try {
    return allowed.has(new URL(origin).origin);
  } catch {
    return false;
  }
}

export function userAgent(headers: Headers): string | null {
  return headers.get("user-agent")?.slice(0, 512) ?? null;
}
