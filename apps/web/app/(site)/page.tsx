import type { Metadata } from "next";
import Link from "next/link";
import { Faq } from "@/components/site/faq";
import { QuadroCard, VideoCard } from "@/components/site/video-card";
import { ReadingCard } from "@/components/site/reading-card";
import { ReadingPreview } from "@/components/site/reading-preview";
import { Section } from "@/components/site/section";
import { buttonVariants } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmailCapture } from "@/components/ui/email-capture";
import { Gold } from "@/components/ui/gold";
import { MARKET_LINKS } from "@/lib/market-classes";
import { AUTHOR, DATA_SOURCES, DOES_AND_DOESNT, FAQ, QUADROS, READINGS, SITE_DESCRIPTION } from "@/content/site";
import { publishedVideos } from "@/lib/videos";
import { JsonLd } from "@/components/site/json-ld";
import { organizationJsonLd } from "@/lib/seo";

export const metadata: Metadata = {
  title: { absolute: "Alpherion Finance — Você sabe o que tem?" },
  description: SITE_DESCRIPTION,
  alternates: { canonical: "/" },
};

// Landing (§5): 10 seções, nesta ordem.
export default function HomePage() {
  const videos = publishedVideos().slice(0, 3);

  return (
    <>
      <JsonLd data={organizationJsonLd()} />
      {/* 1. Hero */}
      <Section className="pt-20 md:pt-28">
        <h1 className="max-w-3xl">
          Você sabe o que <Gold>tem</Gold>?
        </h1>
        <p className="mt-6 max-w-2xl text-lg text-ice-70">
          O Alpherion lê a sua carteira — cripto, ações, FIIs, renda fixa — e devolve cinco leituras de risco, em
          segundos, em português. Não diz o que comprar.
        </p>
        <div className="mt-10">
          <EmailCapture source="hero" />
        </div>
      </Section>

      {/* 2. As cinco leituras */}
      <Section
        id="leituras"
        heading={
          <>
            As cinco <Gold>leituras</Gold>
          </>
        }
        intro="Cada uma responde a uma pergunta sobre a carteira que você já tem. Os números são de uma carteira ilustrativa de R$ 120 mil com 11 ativos."
      >
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {READINGS.map((r) => (
            <ReadingCard key={r.slug} reading={r} href={`/raio-x#${r.slug}`} />
          ))}
          <Card className="flex flex-col justify-between border-dashed">
            <p className="text-ice-70">Quer ver as cinco leituras aplicadas, aba por aba, na mesma carteira?</p>
            <Link href="/raio-x" className={`${buttonVariants({ variant: "secondary" })} mt-6 self-start`}>
              Ver o raio-x completo
            </Link>
          </Card>
        </div>
      </Section>

      {/* 3. Prévia */}
      <Section
        heading={
          <>
            Uma leitura, na <Gold>prática</Gold>
          </>
        }
      >
        <ReadingPreview />
      </Section>

      {/* 4. O que o Alpherion não faz */}
      <Section
        heading={
          <>
            O que o Alpherion <Gold>não</Gold> faz
          </>
        }
      >
        <div className="grid gap-4 md:grid-cols-2">
          <Card>
            <h3 className="font-display text-xl font-semibold text-ok">
              <span aria-hidden="true">✓</span> Faz
            </h3>
            <ul className="mt-4 space-y-2 text-ice-70">
              {DOES_AND_DOESNT.does.map((t) => (
                <li key={t}>{t}</li>
              ))}
            </ul>
          </Card>
          <Card>
            <h3 className="font-display text-xl font-semibold text-risk-text">
              <span aria-hidden="true">✕</span> Não faz
            </h3>
            <ul className="mt-4 space-y-2 text-ice-70">
              {DOES_AND_DOESNT.doesnt.map((t) => (
                <li key={t}>{t}</li>
              ))}
            </ul>
          </Card>
        </div>
      </Section>

      {/* 5. Dados de mercado */}
      <Section
        heading={
          <>
            Dados de <Gold>mercado</Gold>
          </>
        }
        intro="Cotações, indicadores e proventos de toda a B3, Tesouro e cripto — com fonte em cada número."
      >
        {/* A busca global entra com o header do portal (Etapa 4.1). Aqui, os sete caminhos. */}
        <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {MARKET_LINKS.map((link) => (
            <li key={link.href}>
              <Link
                href={link.href}
                className="block rounded-lg border border-navy-3 bg-navy-2 px-4 py-3 hover:border-gold"
              >
                <span className="font-medium">{link.label}</span>
                <span className="mt-1 block text-table text-ice-70">{link.hint}</span>
              </Link>
            </li>
          ))}
        </ul>
        <ul className="mt-6 flex flex-wrap gap-2">
          {DATA_SOURCES.map((s) => (
            <li key={s} className="rounded-full border border-navy-3 px-3 py-1 text-table text-ice-70">
              {s}
            </li>
          ))}
        </ul>
        <p className="mt-4 max-w-2xl text-table text-ice-70">
          Fontes oficiais e públicas. Nenhum número sem fonte e data; nenhuma nota, ranking ou preço-alvo.
        </p>
      </Section>

      {/* 6. Últimos vídeos */}
      <Section
        id="videos"
        heading={
          <>
            Três quadros por <Gold>semana</Gold>
          </>
        }
        intro="Leitura de Mercado na segunda, Raio-X de Carteira na quarta, Tese na sexta. Quinze minutos cada."
      >
        <div className="grid gap-4 md:grid-cols-3">
          {videos.length > 0
            ? videos.map((v) => <VideoCard key={v.id} video={v} />)
            : QUADROS.map((q) => <QuadroCard key={q.slug} quadro={q} />)}
        </div>
        <Link href="/videos" className="mt-6 inline-block text-gold underline decoration-gold/40 underline-offset-4 hover:decoration-gold">
          Todos os vídeos →
        </Link>
      </Section>

      {/* 7. Quem faz */}
      <Section
        heading={
          <>
            Quem <Gold>faz</Gold>
          </>
        }
      >
        <div className="max-w-2xl space-y-3 text-ice-70">
          <p className="text-ice">{AUTHOR.name}</p>
          {AUTHOR.bio.map((line) => (
            <p key={line}>{line}</p>
          ))}
          <Link href="/sobre" className="inline-block text-gold underline decoration-gold/40 underline-offset-4 hover:decoration-gold">
            Sobre o Alpherion →
          </Link>
        </div>
      </Section>

      {/* 8. FAQ */}
      <Section
        id="faq"
        heading={
          <>
            Perguntas <Gold>frequentes</Gold>
          </>
        }
      >
        <Faq items={FAQ} />
      </Section>

      {/* 9. Segundo EmailCapture */}
      <Section className="border-t border-navy-3">
        <h2>
          Entre na <Gold>lista</Gold>
        </h2>
        <p className="mt-4 max-w-2xl text-ice-70">
          Quem está na lista tem a carteira lida primeiro. Enquanto isso, recebe a Leitura de Mercado da semana.
        </p>
        <div className="mt-8">
          <EmailCapture source="footer" />
        </div>
      </Section>

      {/* 10. Rodapé: components/site/footer.tsx (layout) */}
    </>
  );
}
