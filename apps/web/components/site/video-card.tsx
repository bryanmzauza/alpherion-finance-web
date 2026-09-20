import { VideoEmbed } from "@/components/ui/video-embed";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { QUADROS, YOUTUBE_CHANNEL_URL, type Quadro } from "@/content/site";
import type { PublishedVideo } from "@/lib/videos";

const quadroBySlug = (slug: Quadro["slug"]) => QUADROS.find((q) => q.slug === slug)!;

// Vídeo publicado: embed nocookie sob clique. Thumbnail local em public/videos/{id}.jpg.
export function VideoCard({ video }: { video: PublishedVideo }) {
  const quadro = quadroBySlug(video.quadro);
  return (
    <article className="space-y-3">
      <VideoEmbed youtubeId={video.youtubeId} title={video.title} thumbnailSrc={`/videos/${video.id}.jpg`} />
      <Badge tone="gold">{quadro.name}</Badge>
      <h3 className="font-medium">{video.title}</h3>
    </article>
  );
}

// Sem vídeo publicado ainda: o card apresenta o quadro e leva ao canal. Sem data, sem "em breve".
export function QuadroCard({ quadro }: { quadro: Quadro }) {
  return (
    <a
      href={YOUTUBE_CHANNEL_URL}
      target="_blank"
      rel="noopener noreferrer"
      className="block h-full rounded-lg transition-colors hover:[&>div]:border-gold/50"
    >
      <Card className="flex h-full flex-col">
        <p className="text-table text-ice-70">{quadro.day}</p>
        <h3 className="mt-1 font-display text-xl font-semibold">{quadro.name}</h3>
        <p className="mt-3 flex-1 text-table text-ice-70">{quadro.promise}</p>
        <p className="mt-4 text-table text-gold">Ver no YouTube →</p>
      </Card>
    </a>
  );
}
