"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { SearchBox } from "@/components/search/search-box";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { AssetHit } from "@/lib/market";
import { CLASS_LABEL, HIT_CLASS, HIT_REF } from "@/lib/portfolio/labels";

// Lançamento manual (plano 5.3): o ativo vem da mesma busca global do portal — o que
// garante que o símbolo gravado é o do cadastro de mercado (ticker, slug do título ou id
// da cripto), e a valorização encontra o preço depois.

type Picked = { symbol: string; name: string; asset_class: keyof typeof CLASS_LABEL; market_ref: string };

function fromHit(hit: AssetHit): Picked | null {
  if (hit.type === "index") return null;
  return { symbol: hit.code, name: hit.name, asset_class: HIT_CLASS[hit.type], market_ref: HIT_REF[hit.type] };
}

export function ManualTransactionForm({ today }: { today: string }) {
  const router = useRouter();
  const [asset, setAsset] = useState<Picked | null>(null);
  const [status, setStatus] = useState<{ kind: "idle" | "saving" | "saved" | "error"; message?: string }>({ kind: "idle" });

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!asset) {
      setStatus({ kind: "error", message: "Escolha o ativo na busca." });
      return;
    }
    const element = event.currentTarget;
    const form = new FormData(element);
    setStatus({ kind: "saving" });
    const res = await fetch("/api/portfolio/transactions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        asset,
        date: form.get("date"),
        side: form.get("side"),
        quantity: form.get("quantity"),
        price: form.get("price"),
        fees: form.get("fees") || "0",
      }),
    }).catch(() => null);
    if (!res?.ok) {
      const data = (await res?.json().catch(() => null)) as { error?: string } | null;
      setStatus({ kind: "error", message: data?.error ?? "Não foi possível lançar. Confira os campos." });
      return;
    }
    setStatus({ kind: "saved" });
    element.reset();
    router.refresh();
  }

  return (
    <div className="space-y-6">
      <SearchBox
        size="lg"
        label="Ativo"
        placeholder="Ticker, nome da empresa, título do Tesouro ou cripto"
        onPick={(hit) => {
          setAsset(fromHit(hit));
          setStatus({ kind: "idle" });
        }}
      />
      {asset ? (
        <p className="text-table text-ice-70">
          Selecionado: <span className="text-ice">{asset.market_ref === "ticker" ? asset.symbol : asset.name}</span> ·{" "}
          {CLASS_LABEL[asset.asset_class]}
        </p>
      ) : null}

      <form onSubmit={submit} className="grid gap-5 sm:grid-cols-2">
        <fieldset className="sm:col-span-2">
          <legend className="mb-2 text-table text-ice-70">Tipo</legend>
          <div className="flex gap-6">
            <label className="flex items-center gap-2">
              <input type="radio" name="side" value="buy" defaultChecked className="accent-gold" /> Compra
            </label>
            <label className="flex items-center gap-2">
              <input type="radio" name="side" value="sell" className="accent-gold" /> Venda
            </label>
          </div>
        </fieldset>
        <Field id="date" label="Data">
          <Input id="date" name="date" type="date" required max={today} />
        </Field>
        <Field id="quantity" label="Quantidade">
          <Input id="quantity" name="quantity" inputMode="decimal" required placeholder="100" />
        </Field>
        <Field id="price" label="Preço unitário (R$)">
          <Input id="price" name="price" inputMode="decimal" required placeholder="38,52" />
        </Field>
        <Field id="fees" label="Taxas da operação (R$, opcional)">
          <Input id="fees" name="fees" inputMode="decimal" placeholder="0,00" />
        </Field>
        <div className="sm:col-span-2">
          {status.kind === "error" ? (
            <p role="alert" className="mb-4 text-table text-risk-text">
              {status.message}
            </p>
          ) : null}
          {status.kind === "saved" ? (
            <p role="status" className="mb-4 text-table text-ok">
              Lançado. A posição já considera esta movimentação.
            </p>
          ) : null}
          <Button type="submit" disabled={status.kind === "saving"}>
            {status.kind === "saving" ? "Lançando…" : "Lançar"}
          </Button>
        </div>
      </form>
    </div>
  );
}

function Field({ id, label, children }: { id: string; label: string; children: React.ReactNode }) {
  return (
    <div>
      <label htmlFor={id} className="mb-2 block text-table text-ice-70">
        {label}
      </label>
      {children}
    </div>
  );
}
