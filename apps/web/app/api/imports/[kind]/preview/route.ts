import { NextResponse } from "next/server";
import { ApiError, apiUpload } from "@/lib/api-client";
import { sha256 } from "@/lib/hash";
import { requirePortfolio } from "@/lib/portfolio/http";
import { annotatePreview, importPreviewSchema } from "@/lib/portfolio/imports";
import { rateLimit } from "@/lib/rate-limit";

// POST /api/imports/{b3|csv}/preview — arquivo(s) → prévia (site.md §7.4, plano 5.3).
//
// O arquivo passa por aqui só em memória: calcula-se o `sha256` (dedupe por arquivo),
// repassa-se à API, que lê e descarta. Nada do conteúdo vai para log — nem nome de
// arquivo, que pode trazer o nome da pessoa.

const LIMITS = {
  b3: { files: 3, bytes: 5 * 1024 * 1024, api: "/v1/imports/b3/preview" },
  csv: { files: 1, bytes: 2 * 1024 * 1024, api: "/v1/imports/csv/preview" },
} as const;

export async function POST(request: Request, { params }: { params: Promise<{ kind: string }> }): Promise<Response> {
  const { kind } = await params;
  if (kind !== "b3" && kind !== "csv") return NextResponse.json({ error: "Tipo inválido" }, { status: 404 });
  const limit = LIMITS[kind];

  const guard = await requirePortfolio(request);
  if (!guard.ok) return guard.response;
  const { userId, portfolioId } = guard.ctx;

  const rl = await rateLimit("imports", userId, 30, 3600);
  if (!rl.ok) return NextResponse.json({ error: "Muitas importações seguidas; tente daqui a pouco" }, { status: 429 });

  const declared = Number(request.headers.get("content-length") ?? "0");
  if (!declared || declared > limit.files * limit.bytes + 64 * 1024) {
    return NextResponse.json({ error: "Envio maior que o permitido" }, { status: 413 });
  }
  const form = await request.formData().catch(() => null);
  const files = (form?.getAll("files") ?? []).filter((f): f is File => f instanceof File && f.size > 0);
  if (files.length < 1 || files.length > limit.files) {
    return NextResponse.json({ error: `Envie de 1 a ${limit.files} arquivo${limit.files > 1 ? "s" : ""}` }, { status: 422 });
  }
  if (files.some((f) => f.size > limit.bytes)) {
    return NextResponse.json({ error: `Cada arquivo pode ter até ${limit.bytes / 1024 / 1024} MB` }, { status: 413 });
  }

  const buffers = await Promise.all(files.map(async (f) => Buffer.from(await f.arrayBuffer())));
  const hashes = buffers.map((b) => sha256(b));

  let raw: unknown;
  try {
    // Nome neutro: o nome original do arquivo não sai deste processo.
    raw = await apiUpload(
      limit.api,
      buffers.map((b, i) => ({ name: `arquivo-${i + 1}`, data: new Blob([new Uint8Array(b)]) })),
    );
  } catch (error) {
    console.error("[imports] prévia indisponível:", error instanceof ApiError ? error.status : (error as Error).name);
    return NextResponse.json({ error: "Não foi possível ler os arquivos agora. Tente de novo em alguns minutos." }, { status: 502 });
  }

  const parsed = importPreviewSchema.safeParse(raw);
  if (!parsed.success) {
    console.error("[imports] prévia fora do formato esperado");
    return NextResponse.json({ error: "Resposta inesperada ao ler os arquivos" }, { status: 502 });
  }
  const preview = await annotatePreview(userId, portfolioId, parsed.data, hashes);
  return NextResponse.json(preview, { headers: { "Cache-Control": "no-store" } });
}
