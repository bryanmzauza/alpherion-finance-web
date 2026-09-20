"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useId, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { track } from "@/lib/umami";

type Status = "idle" | "sending" | "error";

// Captura de e-mail da landing (§5, seção 1 e 9). POST /api/subscribe → /lista/obrigado.
// Consentimento específico e não pré-marcado (LGPD art. 8); honeypot no campo `website`.
export function EmailCapture({ source = "landing" }: { source?: string }) {
  const id = useId();
  const router = useRouter();
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const data = new FormData(form);
    setStatus("sending");
    setError(null);
    track("subscribe_submit", { source });
    try {
      const res = await fetch("/api/subscribe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: String(data.get("email") ?? ""),
          consent: data.get("consent") === "on",
          website: String(data.get("website") ?? ""),
        }),
      });
      if (res.status === 429) {
        setError("Muitas tentativas. Espere um minuto e tente de novo.");
        setStatus("error");
        return;
      }
      if (!res.ok) {
        setError("Não deu certo agora. Tente de novo em instantes.");
        setStatus("error");
        return;
      }
      router.push("/lista/obrigado");
    } catch {
      setError("Sem conexão. Tente de novo.");
      setStatus("error");
    }
  }

  return (
    <form onSubmit={onSubmit} className="w-full max-w-xl" noValidate>
      <div className="flex flex-col gap-3 sm:flex-row">
        <label htmlFor={`${id}-email`} className="sr-only">
          Seu e-mail
        </label>
        <Input
          id={`${id}-email`}
          name="email"
          type="email"
          inputMode="email"
          autoComplete="email"
          placeholder="seu@email.com"
          required
          maxLength={254}
          aria-invalid={status === "error" ? true : undefined}
          aria-describedby={error ? `${id}-error` : `${id}-micro`}
        />
        <Button type="submit" disabled={status === "sending"} className="sm:shrink-0">
          {status === "sending" ? "Enviando…" : "Entrar na lista"}
        </Button>
      </div>

      {/* Honeypot: invisível para pessoas, preenchido por bots. */}
      <div aria-hidden="true" className="absolute -left-[9999px] h-0 w-0 overflow-hidden">
        <label htmlFor={`${id}-website`}>Website</label>
        <input id={`${id}-website`} name="website" type="text" tabIndex={-1} autoComplete="off" />
      </div>

      <Checkbox
        id={`${id}-consent`}
        name="consent"
        required
        className="mt-4"
        label={
          <>
            Quero receber a Leitura de Mercado e avisos do Alpherion por e-mail. Li a{" "}
            <Link href="/privacidade" className="text-gold underline-offset-4 hover:underline">
              Política de Privacidade
            </Link>
            .
          </>
        }
      />

      {error ? (
        <p id={`${id}-error`} role="alert" className="mt-3 text-table text-risk">
          {error}
        </p>
      ) : (
        <p id={`${id}-micro`} className="mt-3 text-table text-ice-70">
          Grátis. Quem está na lista entra primeiro. Sem spam — no máximo um e-mail por semana.
        </p>
      )}
    </form>
  );
}
