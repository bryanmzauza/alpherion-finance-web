import type { Metadata } from "next";
import Link from "next/link";
import { z } from "zod";
import { Section } from "@/components/site/section";
import { UmamiEvent } from "@/components/site/umami-event";
import { buttonVariants } from "@/components/ui/button";
import { Gold } from "@/components/ui/gold";
import { YOUTUBE_CHANNEL_URL } from "@/content/site";
import { confirmSubscription } from "@/lib/listmonk";

export const metadata: Metadata = {
  title: "Confirmação",
  robots: { index: false },
};

export const dynamic = "force-dynamic";

const tokenSchema = z.uuid();

// /lista/confirmar?t=<uuid do assinante> — link do e-mail de opt-in do Listmonk (§2.1).
export default async function ConfirmarPage({ searchParams }: { searchParams: Promise<{ t?: string }> }) {
  const { t } = await searchParams;
  const token = tokenSchema.safeParse(t);
  let confirmed = false;
  if (token.success) {
    confirmed = await confirmSubscription(token.data).catch(() => false);
  }

  if (!confirmed) {
    return (
      <Section className="pt-20 md:pt-28">
        <h1 className="max-w-3xl">
          Link <Gold>inválido</Gold>
        </h1>
        <p className="mt-6 max-w-2xl text-lg text-ice-70">
          Este link de confirmação não é válido. Se você acabou de se cadastrar, use o link do e-mail mais recente; se
          preferir, cadastre-se de novo.
        </p>
        <Link href="/#faq" className={`${buttonVariants({ variant: "secondary" })} mt-8`}>
          Voltar ao início
        </Link>
      </Section>
    );
  }

  return (
    <Section className="pt-20 md:pt-28">
      <UmamiEvent name="subscribe_confirm" />
      <h1 className="max-w-3xl">
        Você está na <Gold>lista</Gold>
      </h1>
      <p className="mt-6 max-w-2xl text-lg text-ice-70">
        Confirmado. Você recebe a Leitura de Mercado da semana e é avisado primeiro quando o Alpherion abrir.
      </p>
      <p className="mt-8 text-ice-70">Próximo passo: inscreva-se no canal para não perder os três quadros da semana.</p>
      <a
        href={YOUTUBE_CHANNEL_URL}
        target="_blank"
        rel="noopener noreferrer"
        className={`${buttonVariants()} mt-4`}
      >
        Inscrever-se no canal
      </a>
    </Section>
  );
}
