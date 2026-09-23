import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Gold } from "@/components/ui/gold";
import { Input } from "@/components/ui/input";
import { googleEnabled } from "@/lib/auth";
import { ENTRAR_ERRORS, safeNext } from "@/lib/entrar";
import { env } from "@/lib/env";
import { LEGAL } from "@/lib/legal";
import { getSession } from "@/lib/session";

export const metadata: Metadata = { title: "Entrar" };

type Props = { searchParams: Promise<{ erro?: string; next?: string }> };

// /entrar (site.md §2.2): link por e-mail (sem senha) ou Google. Um formulário HTML
// comum, que funciona sem JavaScript; o botão do Google envia o mesmo formulário para
// outra rota (`formAction`), então a caixa de aceite vale para os dois caminhos.
//
// Entrar e criar conta são a mesma coisa: quem ainda não tem conta ganha uma no primeiro
// link. Por isso o aceite de Termos e Privacidade está aqui, desmarcado (LGPD art. 8).
export default async function EntrarPage({ searchParams }: Props) {
  const { erro, next: rawNext } = await searchParams;
  const next = safeNext(rawNext);
  if (await getSession()) redirect(next);

  const message = erro ? ENTRAR_ERRORS[erro] : undefined;
  const termos = `${env.SITE_URL}/termos`;
  const privacidade = `${env.SITE_URL}/privacidade`;

  return (
    <>
      <h1 className="text-3xl md:text-4xl">
        Entre na sua <Gold>carteira</Gold>
      </h1>
      <p className="mt-4 text-ice-70">
        Mandamos um link de acesso para o seu e-mail. Sem senha: o link vale por 15 minutos e só uma vez. Se ainda não
        tem conta, ela é criada nesse primeiro acesso.
      </p>

      {message ? (
        <p role="alert" className="mt-6 rounded-md border border-risk/40 bg-risk/10 px-4 py-3 text-table text-risk-text">
          {message}
        </p>
      ) : null}

      <form action="/api/entrar" method="post" className="mt-8 space-y-5">
        <input type="hidden" name="next" value={next} />
        <div>
          <label htmlFor="email" className="mb-2 block text-table text-ice-70">
            E-mail
          </label>
          <Input id="email" name="email" type="email" required autoComplete="email" inputMode="email" maxLength={254} />
        </div>
        <Checkbox
          id="aceite"
          name="aceite"
          required
          label={
            <>
              Li e aceito os{" "}
              <a href={termos} target="_blank" rel="noopener" className="text-gold underline underline-offset-4">
                Termos de Uso
              </a>{" "}
              (versão {LEGAL.termos.version}) e a{" "}
              <a href={privacidade} target="_blank" rel="noopener" className="text-gold underline underline-offset-4">
                Política de Privacidade
              </a>{" "}
              (versão {LEGAL.privacidade.version}).
            </>
          }
        />
        <Button type="submit" className="w-full">
          Receber link de acesso
        </Button>
        {googleEnabled ? (
          <>
            <p className="text-center text-table text-ice-70">ou</p>
            {/* formNoValidate: o e-mail não é exigido neste caminho; o aceite a rota confere. */}
            <Button type="submit" variant="secondary" className="w-full" formAction="/api/entrar/google" formNoValidate>
              Entrar com Google
            </Button>
          </>
        ) : null}
      </form>

      <p className="mt-8 text-table text-ice-70">
        Guardamos o mínimo: seu e-mail e o que você lançar na carteira, com os números cifrados. Nada é compartilhado com
        corretoras ou anunciantes.
      </p>
    </>
  );
}
