import { AUTHOR, EMAILS, QUADROS, SITE_DESCRIPTION, SITE_NAME, YOUTUBE_CHANNEL_URL } from "@/content/site";
import { env } from "@/lib/env";
import type { PublishedVideo } from "@/lib/videos";

export const siteUrl = (path = "/"): string => new URL(path, env.SITE_URL).toString();

const isPlaceholder = (s: string) => s.startsWith("[");

// JSON-LD `Organization` da home (site.md §9). Só fatos: nome, site, logo, contato, canal.
export function organizationJsonLd(): Record<string, unknown> {
  return {
    "@context": "https://schema.org",
    "@type": "Organization",
    name: SITE_NAME,
    url: siteUrl("/"),
    logo: siteUrl("/icon.png"),
    description: SITE_DESCRIPTION,
    founder: { "@type": "Person", name: AUTHOR.name },
    contactPoint: [
      { "@type": "ContactPoint", contactType: "customer support", email: EMAILS.contato, availableLanguage: "pt-BR" },
    ],
    ...(isPlaceholder(YOUTUBE_CHANNEL_URL) ? {} : { sameAs: [YOUTUBE_CHANNEL_URL] }),
  };
}

// JSON-LD `VideoObject` (um por vídeo publicado). Embed via youtube-nocookie, thumbnail local.
export function videoJsonLd(video: PublishedVideo): Record<string, unknown> {
  const quadro = QUADROS.find((q) => q.slug === video.quadro)!;
  return {
    "@context": "https://schema.org",
    "@type": "VideoObject",
    name: video.title,
    description: quadro.promise,
    thumbnailUrl: [siteUrl(`/videos/${video.id}.jpg`)],
    uploadDate: video.publishedAt,
    embedUrl: `https://www.youtube-nocookie.com/embed/${video.youtubeId}`,
    publisher: { "@type": "Organization", name: SITE_NAME, logo: { "@type": "ImageObject", url: siteUrl("/icon.png") } },
    inLanguage: "pt-BR",
  };
}
