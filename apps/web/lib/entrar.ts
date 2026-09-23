import { z } from "zod";

// Regras do formulário de entrada, sem dependência de servidor (testáveis).

/** Destino depois do login: só caminho interno do app, nunca URL externa (open redirect). */
export function safeNext(raw: string | null | undefined): string {
  if (!raw) return "/inicio";
  if (!raw.startsWith("/") || raw.startsWith("//") || raw.includes("\\")) return "/inicio";
  return raw.slice(0, 200);
}

export const entrarSchema = z.object({
  email: z.email().max(254).transform((e) => e.trim().toLowerCase()),
  // Caixa não pré-marcada (§2.2): o formulário manda "on" só se a pessoa marcou.
  aceite: z.literal("on"),
  next: z.string().max(200).optional(),
});

/** Mensagens da tela de entrada, pelo código que a rota devolve em `?erro=`. */
export const ENTRAR_ERRORS: Record<string, string> = {
  dados: "Confira o e-mail e marque a caixa de aceite para continuar.",
  limite: "Muitas tentativas seguidas. Espere alguns minutos e tente de novo.",
  envio: "Não conseguimos enviar o e-mail agora. Tente de novo em alguns minutos.",
  link: "O link expirou ou já foi usado. Peça um novo abaixo.",
  google: "Não foi possível entrar com o Google. Tente de novo ou use o link por e-mail.",
};
