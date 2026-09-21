import type { Metadata } from "next";
import { QuadroCard, VideoCard } from "@/components/site/video-card";
import { Section } from "@/components/site/section";
import { Gold } from "@/components/ui/gold";
import { QUADROS, YOUTUBE_CHANNEL_URL } from "@/content/site";
import { publishedVideos } from "@/lib/videos";
import { JsonLd } from "@/components/site/json-ld";
import { videoJsonLd } from "@/lib/seo";

export const metadata: Metadata = {
  title: "Vídeos",
  description: "Leitura de Mercado, Raio-X de Carteira e Tese: os três quadros do canal Alpherion Finance no YouTube.",
  alternates: { canonical: "/videos" },
};

// Fonte: content/videos.json. Embeds só via youtube-nocookie e só após clique (§8.5).
export default function VideosPage() {
  const videos = publishedVideos();

  return (
    <>
      {videos.map((v) => (
        <JsonLd key={v.id} data={videoJsonLd(v)} />
      ))}
      <Section className="pt-20 md:pt-28">
        <h1 className="max-w-3xl">
          Três quadros por <Gold>semana</Gold>
        </h1>
        <p className="mt-6 max-w-2xl text-lg text-ice-70">
          Quinze minutos cada. Nenhum ativo é indicado: leitura, diagnóstico e opinião com dado atrás.
        </p>
        <a
          href={YOUTUBE_CHANNEL_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-6 inline-block text-gold underline decoration-gold/40 underline-offset-4 hover:decoration-gold"
        >
          Canal no YouTube →
        </a>
      </Section>

      <Section heading={<>Os <Gold>quadros</Gold></>}>
        <div className="grid gap-4 md:grid-cols-3">
          {QUADROS.map((q) => (
            <QuadroCard key={q.slug} quadro={q} />
          ))}
        </div>
      </Section>

      {videos.length > 0 ? (
        <Section heading={<>Últimos <Gold>vídeos</Gold></>}>
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {videos.map((v) => (
              <VideoCard key={v.id} video={v} />
            ))}
          </div>
        </Section>
      ) : null}
    </>
  );
}
