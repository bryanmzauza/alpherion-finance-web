import { OG_CONTENT_TYPE, OG_SIZE, ogImage } from "@/lib/og";

export const alt = "O raio-x de carteira: cinco leituras de risco";
export const size = OG_SIZE;
export const contentType = OG_CONTENT_TYPE;

export default function Image() {
  return ogImage({ title: "O que é o raio-x de carteira", gold: "raio-x", subtitle: "Concentração · Correlação · Exposição · Drawdown · Liquidez" });
}
