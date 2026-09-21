import type { Metadata } from "next";
import Link from "next/link";
import { z } from "zod";
import { Section } from "@/components/site/section";
import { Gold } from "@/components/ui/gold";
import { EMAILS } from "@/content/site";
import { unsubscribe } from "@/lib/listmonk";

export const metadata: Metadata = {
  title: "Descadastro",
  robots: { index: false },
};

export const dynamic = "force-dynamic";

const tokenSchema = z.uuid();

// /lista/sair?t=<uuid> — descadastro em 1 clique, sem login e sem "tem certeza?" (LGPD art. 18 IX).
export default async function SairPage({ searchParams }: { searchParams: Promise<{ t?: string }> }) {
  const { t } = await searchParams;
  const token = tokenSchema.safeParse(t);
  const done = token.success ? await unsubscribe(token.data).catch(() => false) : false;

  return (
    <Section className="pt-20 md:pt-28">
      {done ? (
        <>
          <h1 className="max-w-3xl">
            Você saiu da <Gold>lista</Gold>
          </h1>
          <p className="mt-6 max-w-2xl text-lg text-ice-70">
            Pronto — nenhum outro e-mail será enviado. Se mudar de ideia, é só se cadastrar de novo.
          </p>
        </>
      ) : (
        <>
          <h1 className="max-w-3xl">
            Link <Gold>inválido</Gold>
          </h1>
          <p className="mt-6 max-w-2xl text-lg text-ice-70">
            Não encontramos esta inscrição. Use o link de descadastro do e-mail mais recente ou escreva para{" "}
            <a href={`mailto:${EMAILS.privacidade}`} className="text-gold underline-offset-4 hover:underline">
              {EMAILS.privacidade}
            </a>{" "}
            que removemos por lá.
          </p>
        </>
      )}
      <Link href="/" className="mt-8 inline-block text-gold underline-offset-4 hover:underline">
        ← Voltar ao início
      </Link>
    </Section>
  );
}
