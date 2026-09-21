import type { MetadataRoute } from "next";
import { SITE_DESCRIPTION, SITE_NAME } from "@/content/site";

// /manifest.webmanifest. Cores do brand kit (§5); ícones gerados do monograma.
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: SITE_NAME,
    short_name: "Alpherion",
    description: SITE_DESCRIPTION,
    lang: "pt-BR",
    start_url: "/",
    display: "browser",
    background_color: "#0B192C",
    theme_color: "#0B192C",
    icons: [
      { src: "/icon.png", sizes: "512x512", type: "image/png" },
      { src: "/apple-icon.png", sizes: "180x180", type: "image/png" },
    ],
  };
}
