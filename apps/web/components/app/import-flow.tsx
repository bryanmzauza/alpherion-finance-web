"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Table, Td, Th, Thead, Tr } from "@/components/ui/table";
import { cn } from "@/lib/cn";
import { currency, date } from "@/lib/format";
import type { AnnotatedPreview } from "@/lib/portfolio/imports";
import { CLASS_LABEL, INCOME_LABEL, quantity } from "@/lib/portfolio/labels";
import { track } from "@/lib/umami";

// Importação em três tempos (plano 5.3): escolher os arquivos → conferir a prévia (com
// o que já está na carteira marcado) → confirmar. Nada é gravado antes do "Confirmar".

type Props = { kind: "b3" | "csv"; maxFiles: number; maxBytes: number; accept: string };

type Phase =
  | { step: "select"; error: string | null }
  | { step: "uploading" }
  | { step: "preview"; preview: AnnotatedPreview; error: string | null }
  | { step: "saving"; preview: AnnotatedPreview }
  | { step: "done"; result: { transactions: number; income: number; positions: number; skipped: number } };

const KIND_LABEL = {
  b3_posicao: "Posição",
  b3_negociacao: "Negociação",
  b3_proventos: "Proventos / movimentação",
  csv: "CSV",
} as const;

const SHOWN = 50;

export function ImportFlow({ kind, maxFiles, maxBytes, accept }: Props) {
  const router = useRouter();
  const [phase, setPhase] = useState<Phase>({ step: "select", error: null });

  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const input = event.currentTarget.elements.namedItem("files") as HTMLInputElement;
    const files = [...(input.files ?? [])];
    if (files.length < 1 || files.length > maxFiles) {
      setPhase({ step: "select", error: `Escolha de 1 a ${maxFiles} arquivo${maxFiles > 1 ? "s" : ""}.` });
      return;
    }
    if (files.some((f) => f.size > maxBytes)) {
      setPhase({ step: "select", error: `Cada arquivo pode ter até ${maxBytes / 1024 / 1024} MB.` });
      return;
    }
    const form = new FormData();
    for (const file of files) form.append("files", file);
    setPhase({ step: "uploading" });
    try {
      const res = await fetch(`/api/imports/${kind}/preview`, { method: "POST", body: form });
      const data = (await res.json().catch(() => null)) as (AnnotatedPreview & { error?: string }) | null;
      if (!res.ok || !data) {
        setPhase({ step: "select", error: data?.error ?? "Não foi possível ler os arquivos." });
        return;
      }
      setPhase({ step: "preview", preview: data, error: null });
    } catch {
      setPhase({ step: "select", error: "Falha de conexão. Tente de novo." });
    }
  }

  async function confirm(preview: AnnotatedPreview) {
    setPhase({ step: "saving", preview });
    const { files, transactions, income, positions, warnings, hashes } = preview;
    const rest = { files, transactions, income, positions, warnings };
    try {
      const res = await fetch("/api/imports/confirm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ preview: rest, hashes }),
      });
      const data = (await res.json().catch(() => null)) as
        | { transactions: number; income: number; positions: number; skipped: number; error?: string }
        | null;
      if (!res.ok || !data) {
        setPhase({ step: "preview", preview, error: data?.error ?? "Não foi possível gravar. Tente de novo." });
        return;
      }
      if (kind === "b3") {
        track("b3_import", { files: preview.files.length, transactions: data.transactions, positions: data.positions });
      }
      setPhase({ step: "done", result: data });
      router.refresh();
    } catch {
      setPhase({ step: "preview", preview, error: "Falha de conexão. Tente de novo." });
    }
  }

  if (phase.step === "select" || phase.step === "uploading") {
    const error = phase.step === "select" ? phase.error : null;
    return (
      <form onSubmit={upload} className="space-y-5">
        <div>
          <label htmlFor="files" className="mb-2 block text-table text-ice-70">
            {maxFiles > 1 ? `Arquivos (até ${maxFiles}, ${maxBytes / 1024 / 1024} MB cada)` : `Arquivo (até ${maxBytes / 1024 / 1024} MB)`}
          </label>
          <input
            id="files"
            name="files"
            type="file"
            accept={accept}
            multiple={maxFiles > 1}
            required
            className="block w-full text-table text-ice-70 file:mr-4 file:h-11 file:cursor-pointer file:rounded-md file:border file:border-navy-3 file:bg-navy-2 file:px-5 file:text-ice hover:file:border-gold"
          />
        </div>
        {error ? (
          <p role="alert" className="text-table text-risk-text">
            {error}
          </p>
        ) : null}
        <Button type="submit" disabled={phase.step === "uploading"}>
          {phase.step === "uploading" ? "Lendo os arquivos…" : "Ver prévia"}
        </Button>
      </form>
    );
  }

  if (phase.step === "done") {
    const r = phase.result;
    return (
      <Card>
        <h2 className="font-display text-xl font-semibold">Importação concluída</h2>
        <ul className="mt-4 space-y-1 text-table text-ice-70">
          <li>{r.transactions} movimentações novas</li>
          <li>{r.income} proventos novos</li>
          <li>{r.positions} posições atualizadas</li>
          {r.skipped > 0 ? <li>{r.skipped} linhas já estavam na carteira e não foram duplicadas</li> : null}
        </ul>
        <div className="mt-6 flex gap-3">
          <Button onClick={() => router.push("/carteira")}>Ver a carteira</Button>
          <Button variant="secondary" onClick={() => setPhase({ step: "select", error: null })}>
            Importar mais
          </Button>
        </div>
      </Card>
    );
  }

  const { preview } = phase;
  const saving = phase.step === "saving";
  const error = phase.step === "preview" ? phase.error : null;
  const newTx = preview.existing.transactions.filter((e) => !e).length;
  const newInc = preview.existing.income.filter((e) => !e).length;
  const nothing = newTx === 0 && newInc === 0 && preview.positions.length === 0;

  return (
    <div className="space-y-8">
      <div className="grid gap-4 md:grid-cols-3">
        {preview.files.map((f) => (
          <Card key={f.file} className="p-5">
            <p className="text-table text-ice-70">Arquivo {f.file}</p>
            <p className="mt-1 font-medium">{f.kind ? KIND_LABEL[f.kind] : "Não reconhecido"}</p>
            <p className="mt-2 text-table text-ice-70">
              {f.rows_ok} de {f.rows_in} linhas lidas
              {preview.alreadyImportedFiles.includes(f.file) ? " · este arquivo já foi importado antes" : ""}
            </p>
          </Card>
        ))}
      </div>

      <p className="text-ice-70">
        {newTx} movimentações novas
        {preview.transactions.length > newTx ? ` (${preview.transactions.length - newTx} já na carteira)` : ""}
        {" · "}
        {newInc} proventos novos
        {preview.income.length > newInc ? ` (${preview.income.length - newInc} já na carteira)` : ""}
        {" · "}
        {preview.positions.length} posições informadas
      </p>

      {preview.positions.length > 0 ? (
        <section>
          <h2 className="text-2xl">Posição atual</h2>
          <p className="mt-2 text-table text-ice-70">
            A quantidade do arquivo de posição passa a valer para cada ativo, no lugar da soma das negociações.
          </p>
          <div className="mt-4">
            <Table caption="Posições da prévia">
              <Thead>
                <Tr>
                  <Th>Ativo</Th>
                  <Th>Classe</Th>
                  <Th className="text-right">Quantidade</Th>
                  <Th className="text-right">Valor informado</Th>
                </Tr>
              </Thead>
              <tbody className="tabular-nums">
                {preview.positions.slice(0, SHOWN).map((p) => (
                  <Tr key={`${p.asset.asset_class}:${p.asset.symbol}`}>
                    <Td>
                      <AssetName name={p.asset.name} symbol={p.asset.symbol} known={p.asset.known} ticker={p.asset.market_ref === "ticker"} />
                    </Td>
                    <Td>{CLASS_LABEL[p.asset.asset_class]}</Td>
                    <Td numeric>{quantity(p.quantity)}</Td>
                    <Td numeric>{currency(p.value_brl)}</Td>
                  </Tr>
                ))}
              </tbody>
            </Table>
          </div>
        </section>
      ) : null}

      {preview.transactions.length > 0 ? (
        <section>
          <h2 className="text-2xl">Movimentações</h2>
          <div className="mt-4">
            <Table caption="Movimentações da prévia">
              <Thead>
                <Tr>
                  <Th>Data</Th>
                  <Th>Ativo</Th>
                  <Th>Tipo</Th>
                  <Th className="text-right">Quantidade</Th>
                  <Th className="text-right">Preço</Th>
                  <Th>Situação</Th>
                </Tr>
              </Thead>
              <tbody className="tabular-nums">
                {preview.transactions.slice(0, SHOWN).map((t, i) => (
                  <Tr key={`${t.origin.file}:${t.origin.row}`} className={cn(preview.existing.transactions[i] && "text-ice-70")}>
                    <Td>{date(t.date)}</Td>
                    <Td>
                      <AssetName name={t.asset.name} symbol={t.asset.symbol} known={t.asset.known} ticker={t.asset.market_ref === "ticker"} />
                    </Td>
                    <Td>{t.side === "buy" ? "Compra" : "Venda"}</Td>
                    <Td numeric>{quantity(t.quantity)}</Td>
                    <Td numeric>{currency(t.price)}</Td>
                    <Td>{preview.existing.transactions[i] ? "já na carteira" : "nova"}</Td>
                  </Tr>
                ))}
              </tbody>
            </Table>
          </div>
          {preview.transactions.length > SHOWN ? (
            <p className="mt-2 text-table text-ice-70">Mostrando {SHOWN} de {preview.transactions.length}.</p>
          ) : null}
        </section>
      ) : null}

      {preview.income.length > 0 ? (
        <section>
          <h2 className="text-2xl">Proventos</h2>
          <div className="mt-4">
            <Table caption="Proventos da prévia">
              <Thead>
                <Tr>
                  <Th>Pagamento</Th>
                  <Th>Ativo</Th>
                  <Th>Tipo</Th>
                  <Th className="text-right">Líquido</Th>
                  <Th>Situação</Th>
                </Tr>
              </Thead>
              <tbody className="tabular-nums">
                {preview.income.slice(0, SHOWN).map((inc, i) => (
                  <Tr key={`${inc.origin.file}:${inc.origin.row}`} className={cn(preview.existing.income[i] && "text-ice-70")}>
                    <Td>{date(inc.date)}</Td>
                    <Td>{inc.asset.symbol}</Td>
                    <Td>{INCOME_LABEL[inc.kind]}</Td>
                    <Td numeric>{currency(inc.net)}</Td>
                    <Td>{preview.existing.income[i] ? "já na carteira" : "novo"}</Td>
                  </Tr>
                ))}
              </tbody>
            </Table>
          </div>
        </section>
      ) : null}

      {preview.warnings.length > 0 ? (
        <Card>
          <h2 className="font-display text-xl font-semibold">Avisos</h2>
          <ul className="mt-4 list-disc space-y-1 pl-6 text-table text-ice-70">
            {preview.warnings.map((w, i) => (
              <li key={i}>
                {w.origin ? `Arquivo ${w.origin.file}, ${w.origin.sheet}, linha ${w.origin.row}: ` : ""}
                {w.message}
              </li>
            ))}
          </ul>
        </Card>
      ) : null}

      {error ? (
        <p role="alert" className="text-table text-risk-text">
          {error}
        </p>
      ) : null}
      <div className="flex flex-wrap gap-3">
        <Button onClick={() => confirm(preview)} disabled={saving || nothing}>
          {saving ? "Gravando…" : nothing ? "Nada novo para importar" : "Confirmar importação"}
        </Button>
        <Button variant="secondary" onClick={() => setPhase({ step: "select", error: null })} disabled={saving}>
          Escolher outros arquivos
        </Button>
      </div>
    </div>
  );
}

function AssetName({ name, symbol, known, ticker }: { name: string; symbol: string; known?: boolean; ticker: boolean }) {
  return (
    <>
      <span className="font-medium text-ice">{ticker ? symbol : name}</span>
      {known === false ? <span className="ml-2 text-xs text-warn">fora do cadastro — confira</span> : null}
    </>
  );
}
