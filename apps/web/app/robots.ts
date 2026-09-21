import type { MetadataRoute } from "next";
import { siteUrl } from "@/lib/seo";

// Site público. O app (app.alpherion.com.br) recebe `Disallow: /` pelo nginx (Etapa 2.6),
// já que este arquivo é estático e não enxerga o host.
export default function robots(): MetadataRoute.Robots {
  return {
    rules: [{ userAgent: "*", allow: "/", disallow: ["/lista/", "/api/", "/design"] }],
    sitemap: siteUrl("/sitemap.xml"),
  };
}
