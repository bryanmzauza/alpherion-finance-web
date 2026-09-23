import nodemailer, { type Transporter } from "nodemailer";
import { env } from "@/lib/env";

// E-mail transacional (magic link) por SMTP — em dev, o Mailpit do compose (§10).
//
// O magic link não passa pelo Listmonk: a lista de e-mail é de quem pediu newsletter, e
// quem entra no app não pediu. Misturar as duas bases faria um login virar inscrição.

let transporter: Transporter | null = null;

function transport(): Transporter {
  if (transporter) return transporter;
  if (!env.SMTP_HOST || !env.SMTP_PORT) {
    throw new Error("SMTP_HOST/SMTP_PORT não configurados — o magic link não tem como sair");
  }
  transporter = nodemailer.createTransport({
    host: env.SMTP_HOST,
    port: env.SMTP_PORT,
    secure: env.SMTP_PORT === 465,
    auth: env.SMTP_USER ? { user: env.SMTP_USER, pass: env.SMTP_PASSWORD } : undefined,
  });
  return transporter;
}

const FROM = () => env.EMAIL_FROM_TRANSACTIONAL ?? "no-reply@alpherion.com.br";

/**
 * E-mail com o link de entrada. Texto curto e sem imagem de rastreio: o e-mail existe
 * para levar ao link, e o link expira em 15 minutos e vale uma vez só.
 */
export async function sendMagicLinkEmail(to: string, url: string): Promise<void> {
  const text = [
    "Olá,",
    "",
    "Use o link abaixo para entrar no Alpherion Finance. Ele vale por 15 minutos e só pode ser usado uma vez:",
    "",
    url,
    "",
    "Se não foi você quem pediu, ignore este e-mail — ninguém entra sem clicar no link.",
    "",
    "Alpherion Finance",
  ].join("\n");

  const html = `<p>Olá,</p>
<p>Use o link abaixo para entrar no Alpherion Finance. Ele vale por <strong>15 minutos</strong> e só pode ser usado uma vez:</p>
<p><a href="${escapeHtml(url)}">Entrar no Alpherion Finance</a></p>
<p style="color:#555">Se não foi você quem pediu, ignore este e-mail — ninguém entra sem clicar no link.</p>
<p>Alpherion Finance</p>`;

  await transport().sendMail({ from: FROM(), to, subject: "Seu link de entrada no Alpherion Finance", text, html });
}

function escapeHtml(value: string): string {
  return value.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
