import type { MetadataRoute } from "next";
import { LEGAL } from "@/lib/legal";
import { siteUrl } from "@/lib/seo";

// Sitemap das páginas da Fase 0. Os sitemaps segmentados por classe de ativo
// (/sitemap/acoes.xml etc.) entram na Etapa 3. /lista/* e /design ficam de fora.
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
    page("/videos", 0.8),
    page("/sobre", 0.6),
    page("/contato", 0.4),
    page("/privacidade", 0.2, new Date(LEGAL.privacidade.date)),
    page("/termos", 0.2, new Date(LEGAL.termos.date)),
    page("/aviso-legal", 0.2, new Date(LEGAL["aviso-legal"].date)),
  ];
}
