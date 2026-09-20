import type { Metadata } from "next";
import Link from "next/link";
import { Section } from "@/components/site/section";
import { Card } from "@/components/ui/card";
import { Gold } from "@/components/ui/gold";
import { AUTHOR, EMAILS, SITE_TAGLINE } from "@/content/site";

export const metadata: Metadata = {
  title: "Sobre",
  description: "Quem faz o Alpherion Finance, a tese por trás dele e o caminho regulatório, dito com transparência.",
  alternates: { canonical: "/sobre" },
};

const LINE = [
  { when: "Hoje", what: "Leitura de mercado, raio-x de carteira com aviso legal, opinião em cripto. Ação e FII: educacional." },
  { when: "Depois do CNPI", what: "Análise de ações e FIIs assinada por analista credenciado." },
  { when: "Depois do registro na CVM (Res. 19)", what: "Consultoria individual: olhar a sua carteira e dizer o que você deve fazer." },
];

export default function SobrePage() {
  return (
    <>
      <Section className="pt-20 md:pt-28">
        <h1 className="max-w-3xl">
          Diagnóstico, não <Gold>recomendação</Gold>
        </h1>
        <p className="mt-6 max-w-2xl text-lg text-ice-70">{SITE_TAGLINE}</p>
      </Section>

      <Section heading={<>A <Gold>tese</Gold></>}>
        <div className="max-w-2xl space-y-4 text-ice-70">
          <p>
            Todo mundo quer te dizer o que comprar. Quase ninguém te diz o que você já tem. A indústria produz recomendação
            demais e diagnóstico de menos — e gente que não entende a própria carteira compra dica.
          </p>
          <p>
            O Alpherion faz o contrário: lê a carteira que existe — cripto, ações, FIIs, renda fixa — e responde cinco
            perguntas com número: você está concentrado? seus ativos andam juntos? a que está exposto sem saber? quanto já
            caiu? em quanto tempo sai? A decisão continua sendo sua.
          </p>
          <p>
            Diagnóstico é a coisa certa a fazer e a coisa permitida a fazer. As duas coincidem, e isso não é coincidência.
          </p>
        </div>
      </Section>

      <Section heading={<>Quem <Gold>faz</Gold></>}>
        <div className="max-w-2xl space-y-3 text-ice-70">
          <p className="text-ice">{AUTHOR.name}</p>
          {AUTHOR.bio.map((line) => (
            <p key={line}>{line}</p>
          ))}
        </div>
      </Section>

      <Section
        heading={<>A linha da <Gold>regulação</Gold></>}
        intro="No Brasil, recomendar investimento é atividade regulada pela CVM. O que este site pode publicar muda conforme a credencial — e isso é dito aqui, não escondido."
      >
        <div className="grid gap-4 md:grid-cols-3">
          {LINE.map((l) => (
            <Card key={l.when}>
              <p className="font-display text-lg font-semibold">{l.when}</p>
              <p className="mt-3 text-table text-ice-70">{l.what}</p>
            </Card>
          ))}
        </div>
        <p className="mt-6 max-w-2xl text-table text-ice-70">
          Nada do que está aqui é recomendação, e nenhuma etapa futura é promessa. Veja o{" "}
          <Link href="/aviso-legal" className="text-gold underline-offset-4 hover:underline">
            aviso legal
          </Link>
          .
        </p>
      </Section>

      <Section heading={<>Fale com a <Gold>gente</Gold></>}>
        <p className="max-w-2xl text-ice-70">
          Dúvidas, correções e pedidos sobre seus dados:{" "}
          <a href={`mailto:${EMAILS.contato}`} className="text-gold underline-offset-4 hover:underline">
            {EMAILS.contato}
          </a>
          . Detalhes em{" "}
          <Link href="/contato" className="text-gold underline-offset-4 hover:underline">
            /contato
          </Link>
          .
        </p>
      </Section>
    </>
  );
}
