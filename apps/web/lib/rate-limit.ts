import Redis from "ioredis";
import { env } from "@/lib/env";

// Rate limit por chave (IP ou usuário) em janela fixa, no Redis (site.md §7.4).
// Chave: rl:{scope}:{id}. Sem Redis configurado ou fora do ar: falha ABERTA com log —
// a borda (Cloudflare) tem o segundo limite.

let client: Redis | null | undefined;

function redis(): Redis | null {
  if (client !== undefined) return client;
  if (!env.REDIS_URL) {
    client = null;
    return client;
  }
  client = new Redis(env.REDIS_URL, {
    lazyConnect: true,
    maxRetriesPerRequest: 1,
    connectTimeout: 2_000,
    enableOfflineQueue: false,
  });
  client.on("error", () => {
    /* logado abaixo por chamada; evita crash por 'unhandled error event' */
  });
  return client;
}

export type RateLimitResult = { ok: boolean; remaining: number };

export async function rateLimit(scope: string, id: string, limit: number, windowSeconds: number): Promise<RateLimitResult> {
  const r = redis();
  if (!r) return { ok: true, remaining: limit };
  const key = `rl:${scope}:${id}`;
  try {
    if (r.status === "wait") await r.connect();
    const count = await r.incr(key);
    if (count === 1) await r.expire(key, windowSeconds);
    return { ok: count <= limit, remaining: Math.max(0, limit - count) };
  } catch (err) {
    console.warn(`[rate-limit] Redis indisponível (${scope}): ${(err as Error).message}`);
    return { ok: true, remaining: limit };
  }
}
