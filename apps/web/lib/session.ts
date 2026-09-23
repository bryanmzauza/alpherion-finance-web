import { headers } from "next/headers";
import { redirect } from "next/navigation";
import { auth, type AuthSession } from "@/lib/auth";

// Sessão do app no servidor. O `proxy.ts` só olha se o cookie existe (barato, sem banco);
// quem decide de verdade é esta checagem, em toda página e rota do app.

export async function getSession(): Promise<AuthSession | null> {
  return auth.api.getSession({ headers: await headers() });
}

/** Sessão obrigatória: sem ela, volta para o `/entrar` com o destino guardado. */
export async function requireSession(next?: string): Promise<AuthSession> {
  const session = await getSession();
  if (!session) {
    redirect(next ? `/entrar?next=${encodeURIComponent(next)}` : "/entrar");
  }
  return session;
}
