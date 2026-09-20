import type { Metadata } from "next";
import Link from "next/link";
import { Section } from "@/components/site/section";
import { Card } from "@/components/ui/card";
import { Gold } from "@/components/ui/gold";
import { EMAILS, LEGAL_ENTITY } from "@/content/site";

export const metadata: Metadata = {
  title: "Contato",
  description: "Canais de contato do Alpherion Finance: atendimento, encarregado de dados (LGPD) e correção de dados de mercado.",
  alternates: { canonical: "/contato" },
};

const CHANNELS = [
  {
    title: "Contato geral",
    email: EMAILS.contato,
    text: "Dúvidas sobre o site, o canal ou o produto. Resposta em até 5 dias úteis.",
  },
  {
    title: "Privacidade e seus dados (LGPD)",
    email: EMAILS.privacidade,
    text: "Canal do encarregado de dados. Acesso, correção, exclusão, portabilidade e revogação de consentimento. Resposta em até 15 dias. Para sair da lista de e-mail, use o link de descadastro em qualquer e-mail — é imediato.",
  },
  {
    title: "Encontrou um erro no dado?",
    email: EMAILS.dados,
    text: "Cotação, indicador ou demonstração com valor errado ou atrasado. Diga o ativo, o número e a fonte que você conferiu. Erro confirmado é corrigido na origem do pipeline.",
  },
];

// Sem formulário no v1 (§2.1): só e-mails.
export default function ContatoPage() {
  return (
    <>
      <Section className="pt-20 md:pt-28">
        <h1 className="max-w-3xl">
          Fale com a <Gold>gente</Gold>
        </h1>
        <p className="mt-6 max-w-2xl text-lg text-ice-70">Três canais, todos por e-mail.</p>
      </Section>
      <Section>
        <div className="grid gap-4 md:grid-cols-3">
          {CHANNELS.map((c) => (
            <Card key={c.email} className="flex flex-col">
              <h2 className="font-display text-xl font-semibold">{c.title}</h2>
              <p className="mt-3 flex-1 text-table text-ice-70">{c.text}</p>
              <a href={`mailto:${c.email}`} className="mt-4 break-all text-gold underline-offset-4 hover:underline">
                {c.email}
              </a>
            </Card>
          ))}
        </div>
        <p className="mt-8 text-table text-ice-70">
          {LEGAL_ENTITY.razaoSocial} · CNPJ {LEGAL_ENTITY.cnpj} · {LEGAL_ENTITY.endereco}, {LEGAL_ENTITY.cidadeUf}. Base
          legal e prazos na{" "}
          <Link href="/privacidade" className="text-gold underline-offset-4 hover:underline">
            Política de Privacidade
          </Link>
          .
        </p>
      </Section>
    </>
  );
}
