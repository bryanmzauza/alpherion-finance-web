import type { Metadata } from "next";
import Link from "next/link";
import { connection } from "next/server";
import { Card } from "@/components/ui/card";
import { Gold } from "@/components/ui/gold";
import { EMAILS } from "@/content/site";

export const metadata: Metadata = { title: "Verifique seu e-mail" };

// Depois de pedir o link (site.md §2.2). A mesma tela para e-mail com ou sem conta.
// Dinâmica de propósito: rota do app recebe CSP com nonce, e nonce só existe em render
// por request (página estática sairia sem ele e teria os scripts bloqueados).
export default async function VerificarPage() {
  await connection();
  return (
    <>
      <h1 className="text-3xl md:text-4xl">
        Confira seu <Gold>e-mail</Gold>
      </h1>
      <p className="mt-4 text-ice-70">
        Se o endereço estiver certo, o link de acesso chega em instantes. Ele vale por 15 minutos e só pode ser usado
        uma vez.
      </p>
      <Card className="mt-8">
        <h2 className="font-display text-xl font-semibold">Não chegou?</h2>
        <ul className="mt-4 list-disc space-y-2 pl-6 text-table text-ice-70">
          <li>Olhe a pasta de spam ou promoções.</li>
          <li>Confira se o e-mail foi digitado certo.</li>
          <li>Se passou dos 15 minutos, peça um novo link.</li>
          <li>
            Se nada resolver, escreva para <span className="text-ice">{EMAILS.contato}</span>.
          </li>
        </ul>
      </Card>
      <Link href="/entrar" className="mt-8 inline-block text-gold underline decoration-gold/40 underline-offset-4 hover:decoration-gold">
        ← Pedir outro link
      </Link>
    </>
  );
}
