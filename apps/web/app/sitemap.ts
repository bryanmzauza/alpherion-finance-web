import type { MetadataRoute } from "next";
import { LEGAL } from "@/lib/legal";
import { MARKET_CLASSES } from "@/lib/market-classes";
import { siteUrl } from "@/lib/seo";

// Sitemap das páginas fixas. As páginas de ativo ficam nos sitemaps por classe
// (/sitemap/acoes.xml etc.), que o robots.txt também anuncia. /lista/* e /design ficam
// de fora (robots.ts).
const BUILT_AT = new Date();

export default function sitemap(): MetadataRoute.Sitemap {
  const page = (path: string, priority: number, lastModified: Date = BUILT_AT): MetadataRoute.Sitemap[number] => ({
    url: siteUrl(path),
    lastModified,
    changeFrequency: "weekly",
    priority,
  });

  return [
    page("/", 1),
    page("/raio-x", 0.9),
    ...MARKET_CLASSES.map((c) => page(`/${c.slug}`, 0.8)),
    page("/videos", 0.8),
    page("/sobre", 0.6),
    page("/contato", 0.4),
    page("/privacidade", 0.2, new Date(LEGAL.privacidade.date)),
    page("/termos", 0.2, new Date(LEGAL.termos.date)),
    page("/aviso-legal", 0.2, new Date(LEGAL["aviso-legal"].date)),
  ];
}
