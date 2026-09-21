import { OG_CONTENT_TYPE, OG_SIZE, ogImage } from "@/lib/og";

export const alt = "Vídeos do Alpherion Finance";
export const size = OG_SIZE;
export const contentType = OG_CONTENT_TYPE;

export default function Image() {
  return ogImage({ title: "Três quadros por semana", gold: "semana", subtitle: "Leitura de Mercado · Raio-X de Carteira · Tese" });
}
