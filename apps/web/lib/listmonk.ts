import { LEGAL_ENTITY } from "@/content/site";
import { env } from "@/lib/env";

// Cliente mínimo da API do Listmonk (site.md §4.1: o Listmonk é a fonte da verdade da lista).
// Basic auth com usuário de API (LISTMONK_API_USER:LISTMONK_API_TOKEN).
//
// Double opt-in: o e-mail de confirmação é enviado por NÓS pela API transacional do Listmonk
// (template criado por infra/scripts/listmonk-setup.py) com link para SITE_URL/lista/confirmar?t=<uuid>.
// O opt-in nativo do Listmonk fica desligado — o template dele é de sistema e apontaria para a página dele.

export class ListmonkError extends Error {
  constructor(
    public readonly status: number,
    public readonly operation: string,
  ) {
    super(`Listmonk ${operation} respondeu ${status}`);
    this.name = "ListmonkError";
  }
}

type Subscriber = { id: number; uuid: string; email: string; status: string };

type ListmonkConfig = { url: string; user: string; token: string; listId: number; optinTemplateId: number; fromEmail: string };

function config(): ListmonkConfig {
  const { LISTMONK_URL, LISTMONK_API_USER, LISTMONK_API_TOKEN, LISTMONK_LIST_ID, LISTMONK_OPTIN_TEMPLATE_ID, EMAIL_FROM_TRANSACTIONAL } = env;
  if (!LISTMONK_URL || !LISTMONK_API_USER || !LISTMONK_API_TOKEN || !LISTMONK_LIST_ID || !LISTMONK_OPTIN_TEMPLATE_ID) {
    throw new ListmonkError(0, "config");
  }
  return {
    url: LISTMONK_URL.replace(/\/$/, ""),
    user: LISTMONK_API_USER,
    token: LISTMONK_API_TOKEN,
    listId: LISTMONK_LIST_ID,
    optinTemplateId: LISTMONK_OPTIN_TEMPLATE_ID,
    fromEmail: EMAIL_FROM_TRANSACTIONAL ?? "no-reply@alpherion.com.br",
  };
}

async function call<T>(
  operation: string,
  path: string,
  init: RequestInit & { json?: unknown } = {},
): Promise<{ status: number; data: T | null }> {
  const cfg = config();
  const { json, headers, ...rest } = init;
  const res = await fetch(`${cfg.url}/api${path}`, {
    ...rest,
    headers: {
      Authorization: `Basic ${Buffer.from(`${cfg.user}:${cfg.token}`).toString("base64")}`,
      Accept: "application/json",
      ...(json !== undefined ? { "Content-Type": "application/json" } : {}),
      ...headers,
    },
    body: json !== undefined ? JSON.stringify(json) : undefined,
    signal: AbortSignal.timeout(8_000),
    cache: "no-store",
  });
  const body = res.status === 204 ? null : ((await res.json().catch(() => null)) as { data?: T } | null);
  return { status: res.status, data: body?.data ?? null };
}

function query(where: string): Promise<{ status: number; data: { results: Subscriber[] } | null }> {
  return call<{ results: Subscriber[] }>("subscribers.query", `/subscribers?query=${encodeURIComponent(where)}&per_page=1`);
}

async function findByEmail(email: string): Promise<Subscriber | null> {
  const res = await query(`subscribers.email = '${email.replace(/'/g, "''")}'`);
  return res.data?.results[0] ?? null;
}

/** UUID vem do link do e-mail; já validado por zod antes de chegar aqui. */
export async function findByUuid(uuid: string): Promise<Subscriber | null> {
  const res = await query(`subscribers.uuid = '${uuid}'`);
  return res.data?.results[0] ?? null;
}

async function sendOptin(sub: Subscriber): Promise<void> {
  const cfg = config();
  const res = await call("tx.send", "/tx", {
    method: "POST",
    json: {
      subscriber_email: sub.email,
      template_id: cfg.optinTemplateId,
      from_email: `Alpherion Finance <${cfg.fromEmail}>`,
      content_type: "html",
      data: {
        confirm_url: `${env.SITE_URL}/lista/confirmar?t=${sub.uuid}`,
        legal_entity: `${LEGAL_ENTITY.razaoSocial} · CNPJ ${LEGAL_ENTITY.cnpj} · ${LEGAL_ENTITY.cidadeUf}`,
      },
    },
  });
  if (res.status !== 200) throw new ListmonkError(res.status, "tx.send");
}

/**
 * Inscreve o e-mail na lista (não confirmado) e envia o e-mail de confirmação.
 * E-mail já cadastrado → garante a lista e reenvia. Retorno idêntico nos dois casos (sem enumeração).
 */
export async function subscribe(email: string): Promise<void> {
  const cfg = config();
  const created = await call<Subscriber>("subscribers.create", "/subscribers", {
    method: "POST",
    json: {
      email,
      name: email.split("@")[0]?.slice(0, 64) ?? "assinante",
      status: "enabled",
      lists: [cfg.listId],
      preconfirm_subscriptions: false,
    },
  });

  let sub: Subscriber | null = created.data;
  if (created.status === 409) {
    sub = await findByEmail(email);
    if (!sub) throw new ListmonkError(409, "subscribers.create");
    if (sub.status === "blocklisted") return; // pediu para nunca mais receber: silêncio
    await call("subscribers.lists", "/subscribers/lists", {
      method: "PUT",
      json: { ids: [sub.id], action: "add", target_list_ids: [cfg.listId], status: "unconfirmed" },
    });
  } else if (created.status !== 200 || !sub) {
    throw new ListmonkError(created.status, "subscribers.create");
  }

  await sendOptin(sub);
}

/** /lista/confirmar?t= — marca a inscrição na lista como confirmada. */
export async function confirmSubscription(uuid: string): Promise<boolean> {
  const cfg = config();
  const sub = await findByUuid(uuid);
  if (!sub) return false;
  const res = await call("subscribers.lists", "/subscribers/lists", {
    method: "PUT",
    json: { ids: [sub.id], action: "add", target_list_ids: [cfg.listId], status: "confirmed" },
  });
  return res.status === 200;
}

/** /lista/sair?t= — descadastro em 1 clique (LGPD art. 18 IX). */
export async function unsubscribe(uuid: string): Promise<boolean> {
  const cfg = config();
  const sub = await findByUuid(uuid);
  if (!sub) return false;
  const res = await call("subscribers.lists", "/subscribers/lists", {
    method: "PUT",
    json: { ids: [sub.id], action: "unsubscribe", target_list_ids: [cfg.listId] },
  });
  return res.status === 200;
}
