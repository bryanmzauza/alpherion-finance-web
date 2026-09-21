import Script from "next/script";
import { env } from "@/lib/env";

// Umami self-hosted, sem cookie, sem PII (site.md §3.4, §8.5). Só entra quando configurado.
// `nonce` vem do proxy (CSP) — ligado na sub-etapa 2.4.
export function Analytics({ nonce }: { nonce?: string }) {
  if (!env.UMAMI_SCRIPT_URL || !env.UMAMI_WEBSITE_ID) return null;
  return (
    <Script
      src={env.UMAMI_SCRIPT_URL}
      data-website-id={env.UMAMI_WEBSITE_ID}
      data-do-not-track="true"
      strategy="afterInteractive"
      nonce={nonce}
    />
  );
}
