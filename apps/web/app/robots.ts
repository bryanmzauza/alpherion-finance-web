import type { MetadataRoute } from "next";
import { EXTRA_SITEMAPS } from "@/lib/sitemaps";
import { siteUrl } from "@/lib/seo";

// Site público. O app (app.alpherion.com.br) recebe `Disallow: /` pelo nginx (Etapa 2.6),
// já que este arquivo é estático e não enxerga o host.
export default function robots(): MetadataRoute.Robots {
  return {
    rules: [{ userAgent: "*", allow: "/", disallow: ["/lista/", "/api/", "/design"] }],
    // Um sitemap por classe além do geral: milhares de URLs somadas passariam do
    // limite de 50 mil de um arquivo só, e segmentado dá para ver qual classe o
    // Google não está indexando.
    sitemap: [
      siteUrl("/sitemap.xml"),
      ...EXTRA_SITEMAPS.map((slug) => siteUrl(`/sitemaps/${slug}.xml`)),
    ],
  };
}
