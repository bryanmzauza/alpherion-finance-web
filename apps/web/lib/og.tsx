import { readFile } from "node:fs/promises";
import path from "node:path";
import { ImageResponse } from "next/og";
import { SITE_NAME, SITE_TAGLINE } from "@/content/site";

// Imagem Open Graph no estilo da thumbnail (site.md §9): navy, uma palavra dourada
// no título, tagline em Inter. Usado pelos opengraph-image.tsx de cada rota.
// Fontes em WOFF (o Satori não lê WOFF2); só existem para este gerador.
// A OG da página do ativo é **dinâmica** (são milhares de tickers), então este gerador
// roda em runtime dentro do standalone — por isso o Dockerfile copia `app/fonts/og`
// para a imagem. Sem elas, a OG do ativo quebraria só em produção.

export const OG_SIZE = { width: 1200, height: 630 };
export const OG_CONTENT_TYPE = "image/png";

const NAVY = "#0B192C";
const GOLD = "#C5A059";
const ICE = "#F8F9FA";
const ICE_70 = "rgba(248,249,250,0.7)";

const loadFont = async (file: string): Promise<ArrayBuffer> => {
  const buf = await readFile(path.join(process.cwd(), "app", "fonts", "og", file));
  return buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength) as ArrayBuffer;
};

/** Divide o título em [antes, palavra dourada, depois]; a palavra dourada é a 1ª ocorrência (sem diferenciar maiúsculas). */
export function splitGold(title: string, gold: string): [string, string, string] {
  const i = title.toLowerCase().indexOf(gold.toLowerCase());
  if (i < 0) return [title, "", ""];
  return [title.slice(0, i), title.slice(i, i + gold.length), title.slice(i + gold.length)];
}

type Props = {
  title: string;
  /** No máximo uma palavra dourada por título (§5). */
  gold: string;
  subtitle?: string;
};

export async function ogImage({ title, gold, subtitle = SITE_TAGLINE }: Props): Promise<ImageResponse> {
  const [playfair, inter] = await Promise.all([
    loadFont("playfair-display-600.woff"),
    loadFont("inter-400.woff"),
  ]);
  const [before, word, after] = splitGold(title, gold);
  const fontSize = title.length > 40 ? 64 : 80;

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: "72px 80px",
          background: NAVY,
          color: ICE,
          fontFamily: "Inter",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 16, fontSize: 28, color: ICE_70 }}>
          <div style={{ width: 14, height: 14, borderRadius: 7, background: GOLD }} />
          {SITE_NAME}
        </div>
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            fontFamily: "Playfair Display",
            fontSize,
            lineHeight: 1.15,
            maxWidth: 1040,
            textWrap: "balance",
          }}
        >
          {/* pre-wrap: o Satori colapsa espaços nas bordas de cada span */}
          <span style={{ whiteSpace: "pre-wrap" }}>{before}</span>
          {word ? <span style={{ color: GOLD, whiteSpace: "pre-wrap" }}>{word}</span> : null}
          <span style={{ whiteSpace: "pre-wrap" }}>{after}</span>
        </div>
        <div style={{ display: "flex", alignItems: "flex-end", gap: 48, fontSize: 28, color: ICE_70 }}>
          <span style={{ flex: 1 }}>{subtitle}</span>
          <span style={{ flexShrink: 0 }}>alpherion.com.br</span>
        </div>
      </div>
    ),
    {
      ...OG_SIZE,
      fonts: [
        { name: "Playfair Display", data: playfair, weight: 600, style: "normal" },
        { name: "Inter", data: inter, weight: 400, style: "normal" },
      ],
    },
  );
}
