import { z } from "zod";
import raw from "@/content/videos.json";

// content/videos.json é a fonte de /videos e da seção "Últimos vídeos" da landing.
// Um vídeo só aparece embedado quando tem youtubeId; até lá o card aponta para o canal.
const videoSchema = z.object({
  id: z.string(),
  quadro: z.enum(["leitura", "raio-x", "tese"]),
  title: z.string().min(1),
  gold: z.string().min(1),
  youtubeId: z.string().regex(/^[A-Za-z0-9_-]{11}$/).nullable(),
  publishedAt: z.iso.date().nullable(),
});

export type Video = z.infer<typeof videoSchema>;

export const videos: Video[] = z.array(videoSchema).parse(raw);

export type PublishedVideo = Video & { youtubeId: string; publishedAt: string };

export const publishedVideos = (): PublishedVideo[] =>
  videos
    .filter((v): v is PublishedVideo => v.youtubeId !== null && v.publishedAt !== null)
    .sort((a, b) => b.publishedAt.localeCompare(a.publishedAt));
