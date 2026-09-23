import { env } from "@/lib/env";

// Único caminho do web para a API (site.md §3.2): token de serviço do cliente "web".
// O web nunca lê o schema `market` direto.

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly path: string,
    message?: string,
  ) {
    super(message ?? `API respondeu ${status} em ${path}`);
    this.name = "ApiError";
  }
}

type ApiFetchInit = Omit<RequestInit, "body"> & {
  body?: unknown;
  /** ISR: segundos de revalidação para o cache do fetch do Next. */
  revalidate?: number | false;
};

export async function apiFetch<T>(path: string, init: ApiFetchInit = {}): Promise<T> {
  const { body, revalidate, headers, ...rest } = init;
  const res = await fetch(`${env.API_URL}${path}`, {
    ...rest,
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${env.API_SERVICE_TOKEN_WEB}`,
      ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
      ...headers,
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
    ...(revalidate !== undefined ? { next: { revalidate } } : {}),
  });

  if (!res.ok) {
    throw new ApiError(res.status, path);
  }
  return (await res.json()) as T;
}

/**
 * Envio de arquivos (multipart) — só para a prévia de importação. O arquivo passa pela
 * memória deste processo e segue direto para a API; não é gravado nem logado.
 */
export async function apiUpload<T>(path: string, files: { name: string; data: Blob }[]): Promise<T> {
  const form = new FormData();
  for (const file of files) form.append("files", file.data, file.name);
  const res = await fetch(`${env.API_URL}${path}`, {
    method: "POST",
    headers: { Accept: "application/json", Authorization: `Bearer ${env.API_SERVICE_TOKEN_WEB}` },
    body: form,
    cache: "no-store",
  });
  if (!res.ok) throw new ApiError(res.status, path);
  return (await res.json()) as T;
}
