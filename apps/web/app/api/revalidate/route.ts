import { revalidatePath } from "next/cache";
import { NextResponse } from "next/server";
import { z } from "zod";

// Revalidação sob demanda das páginas de mercado (site.md §3.6).
//
// Quem chama é o job `revalidate_pages` do worker, depois de cada carga. Sem isto, o
// visitante veria o dado de ontem até o `revalidate` por tempo expirar — e o tempo
// existe só como rede de segurança.
//
// O worker manda **caminhos**, nunca dado: a fronteira do §3.2 continua de pé (o `web`
// é dono do schema `app`, a API do `market`, e nenhum dos dois lê o schema do outro).

const schema = z.object({
  paths: z.array(z.string().startsWith("/").max(200)).min(1).max(500),
});

export async function POST(request: Request) {
  const expected = process.env.REVALIDATE_TOKEN;
  if (!expected) {
    // Sem token configurado, a rota fica fechada: melhor 503 do que um endpoint que
    // qualquer um pode usar para forçar rebuild.
    return NextResponse.json({ error: "revalidação não configurada" }, { status: 503 });
  }

  const header = request.headers.get("authorization") ?? "";
  const token = header.startsWith("Bearer ") ? header.slice(7) : "";
  if (!timingSafeEqual(token, expected)) {
    return NextResponse.json({ error: "token inválido" }, { status: 401 });
  }

  const body = schema.safeParse(await request.json().catch(() => null));
  if (!body.success) {
    return NextResponse.json({ error: "corpo inválido" }, { status: 422 });
  }

  for (const path of body.data.paths) {
    revalidatePath(path);
  }
  return NextResponse.json({ revalidated: body.data.paths.length });
}

/** Comparação em tempo constante, sem sair cedo no primeiro caractere diferente. */
function timingSafeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i += 1) {
    diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return diff === 0;
}
