import type { Metadata } from "next";
import Link from "next/link";
import { Section } from "@/components/site/section";
import { Card } from "@/components/ui/card";
import { Gold } from "@/components/ui/gold";
import { EMAILS } from "@/content/site";

export const metadata: Metadata = {
  title: "Verifique seu e-mail",
  robots: { index: false },
};

// Pós-cadastro (§2.1): double opt-in exige clicar no link do e-mail.
export default function ObrigadoPage() {
  return (
    <Section className="pt-20 md:pt-28">
      <h1 className="max-w-3xl">
        Falta um <Gold>clique</Gold>
      </h1>
      <p className="mt-6 max-w-2xl text-lg text-ice-70">
        Enviamos um e-mail de confirmação. Abra e clique no link para entrar na lista — sem isso, não enviamos nada.
      </p>
      <Card className="mt-10 max-w-2xl">
        <h2 className="font-display text-xl font-semibold">Não chegou?</h2>
        <ul className="mt-4 list-disc space-y-2 pl-6 text-ice-70">
          <li>Pode levar alguns minutos.</li>
          <li>Olhe a pasta de spam ou promoções e, se estiver lá, marque como &ldquo;não é spam&rdquo;.</li>
          <li>Confira se o e-mail foi digitado certo. Se não, volte e cadastre de novo.</li>
          <li>
            Adicione <span className="text-ice">{EMAILS.contato}</span> aos contatos para os próximos chegarem na caixa de
            entrada.
          </li>
        </ul>
      </Card>
      <Link href="/" className="mt-8 inline-block text-gold underline decoration-gold/40 underline-offset-4 hover:decoration-gold">
        ← Voltar ao início
      </Link>
    </Section>
  );
}
