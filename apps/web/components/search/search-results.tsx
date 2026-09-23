"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState, type RefObject } from "react";
import type { AssetHit, AssetSearchResult } from "@/lib/market";
import { GROUP_LABELS, MIN_QUERY, hitHref } from "@/lib/asset-search";
import { track } from "@/lib/umami";
import { cn } from "@/lib/cn";
import type { ComboboxState } from "./search-box";

// A parte pesada da busca global — só baixada no foco do campo (ver `search-box.tsx`).
//
// Padrão de combobox com lista do WAI-ARIA: o foco fica sempre no `<input>`, e a opção
// ativa é anunciada por `aria-activedescendant`. Teclado: ↓/↑ percorrem as opções (dando
// a volta), Enter abre a opção ativa, Esc fecha, e Enter **sem** opção ativa envia o
// formulário para `/busca?q=` — o comportamento padrão, que não é interceptado.

type Props = {
  query: string;
  inputRef: RefObject<HTMLInputElement | null>;
  listId: string;
  onStateChange: (state: ComboboxState) => void;
};

type Status = "idle" | "loading" | "ready" | "error" | "limited";

/** Espera entre teclas antes de perguntar: "petr4" não precisa de cinco requisições. */
const DEBOUNCE_MS = 180;

/** Resultados já buscados nesta visita — voltar uma letra não refaz a requisição. */
const cache = new Map<string, AssetSearchResult>();

export default function SearchResults({ query, inputRef, listId, onStateChange }: Props) {
  const router = useRouter();
  const term = query.trim();
  const key = term.toLowerCase();
  const searchable = term.length >= MIN_QUERY;

  // Estado guardado **por termo**: o que vale para "petr" não vale para "petr4". O que a
  // tela mostra é derivado do termo atual, sem efeito que "limpe" estado a cada tecla.
  const [fetched, setFetched] = useState<{ key: string; status: Status; result: AssetSearchResult | null }>({
    key: "",
    status: "idle",
    result: null,
  });
  const [cursor, setCursor] = useState<{ key: string; index: number }>({ key: "", index: -1 });
  const [focused, setFocused] = useState(() => document.activeElement === inputRef.current);
  const [closedFor, setClosedFor] = useState<string | null>(null);

  const cached = searchable ? cache.get(key) : undefined;
  const status: Status = !searchable ? "idle" : cached ? "ready" : fetched.key === key ? fetched.status : "loading";
  // Enquanto a resposta nova não chega, a lista anterior continua na tela (sem piscar).
  const result = !searchable ? null : (cached ?? fetched.result);
  const active = cursor.key === key ? cursor.index : -1;
  const open = focused && searchable && closedFor !== key;

  // Opções na ordem da tela, com o link de "ver todos" no fim.
  const options = useMemo(() => {
    const hits = result?.groups.flatMap((group) => group.items) ?? [];
    return [
      ...hits.map((hit) => ({ kind: "hit" as const, hit, href: hitHref(hit) })),
      ...(searchable
        ? [{ kind: "all" as const, hit: null, href: `/busca?q=${encodeURIComponent(term)}` }]
        : []),
    ];
  }, [result, searchable, term]);

  const optionId = (index: number) => `${listId}-${index}`;
  const setActive = (index: number) => setCursor({ key, index });

  // Busca com espera entre teclas e cancelamento da requisição anterior.
  useEffect(() => {
    if (!searchable || cache.has(key)) return;
    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      try {
        const response = await fetch(`/api/market/search?q=${encodeURIComponent(term)}`, {
          signal: controller.signal,
          headers: { Accept: "application/json" },
        });
        if (response.status === 429) {
          setFetched({ key, status: "limited", result: null });
          return;
        }
        if (!response.ok) throw new Error(String(response.status));
        const data = (await response.json()) as AssetSearchResult;
        cache.set(key, data);
        setFetched({ key, status: "ready", result: data });
      } catch (error) {
        if ((error as Error).name !== "AbortError") setFetched({ key, status: "error", result: null });
      }
    }, DEBOUNCE_MS);

    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [key, term, searchable]);

  // Informa a casca (que é dona do `<input>`) para os atributos ARIA.
  const activeId = open && active >= 0 ? optionId(active) : null;
  useEffect(() => {
    onStateChange({ open, activeId });
  }, [open, activeId, onStateChange]);

  // Teclado e foco no próprio `<input>`.
  useEffect(() => {
    const input = inputRef.current;
    if (!input) return;

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "ArrowDown" || event.key === "ArrowUp") {
        if (options.length === 0) return;
        event.preventDefault();
        setClosedFor(null);
        const step = event.key === "ArrowDown" ? 1 : -1;
        const next =
          active < 0 ? (step === 1 ? 0 : options.length - 1) : (active + step + options.length) % options.length;
        setActive(next);
      } else if (event.key === "Enter") {
        if (open && active >= 0 && options[active]) {
          event.preventDefault();
          select(active);
        }
        // Sem opção ativa: o formulário segue para /busca?q= (comportamento padrão).
      } else if (event.key === "Escape") {
        if (open) {
          event.preventDefault();
          setClosedFor(key);
          setActive(-1);
        }
      }
    }
    function onFocus() {
      setFocused(true);
      setClosedFor(null);
    }
    function onBlur() {
      setFocused(false);
    }

    input.addEventListener("keydown", onKeyDown);
    input.addEventListener("focus", onFocus);
    input.addEventListener("blur", onBlur);
    return () => {
      input.removeEventListener("keydown", onKeyDown);
      input.removeEventListener("focus", onFocus);
      input.removeEventListener("blur", onBlur);
    };
  });

  function select(index: number) {
    const option = options[index];
    if (!option) return;
    track("search_select", {
      kind: option.kind === "all" ? "todos" : option.hit.type,
      position: index + 1,
    });
    setClosedFor(key);
    inputRef.current?.blur();
    router.push(option.href);
  }

  const total = result?.groups.reduce((sum, group) => sum + group.items.length, 0) ?? 0;
  const message =
    status === "loading" && !result
      ? "Buscando…"
      : status === "error"
        ? "A busca está indisponível agora. Enter leva à página de resultados."
        : status === "limited"
          ? "Muitas buscas seguidas. Espere um minuto e tente de novo."
          : status === "ready" && total === 0
            ? `Nada encontrado para “${term}”.`
            : null;

  let index = -1;
  return (
    <>
      <p className="sr-only" aria-live="polite">
        {status === "ready" ? `${total} ${total === 1 ? "resultado" : "resultados"}` : message}
      </p>
      <div
        id={listId}
        role="listbox"
        aria-label="Resultados da busca"
        // O clique numa opção não pode tirar o foco do campo antes de navegar.
        onMouseDown={(event) => event.preventDefault()}
        className={cn(
          "absolute left-0 right-0 top-full z-40 mt-1 max-h-[70vh] min-w-72 overflow-y-auto rounded-md border border-navy-3 bg-navy-2 py-2 text-table shadow-xl",
          open ? "block" : "hidden",
        )}
      >
        {message ? <p className="px-3 py-2 text-ice-70">{message}</p> : null}
        {result?.groups.map((group) => {
          const labelId = `${listId}-g-${group.asset_class}`;
          return (
            <div key={group.asset_class} role="group" aria-labelledby={labelId}>
              <p id={labelId} className="px-3 pt-2 pb-1 text-xs uppercase tracking-wide text-ice-70">
                {GROUP_LABELS[group.asset_class]}
              </p>
              {group.items.map((hit) => {
                index += 1;
                return (
                  <Option
                    key={`${hit.type}:${hit.code}`}
                    id={optionId(index)}
                    hit={hit}
                    active={index === active}
                    position={index}
                    onSelect={select}
                    onHover={setActive}
                  />
                );
              })}
            </div>
          );
        })}
        {term.length >= MIN_QUERY ? (
          <div
            id={optionId(options.length - 1)}
            role="option"
            aria-selected={active === options.length - 1}
            onClick={() => select(options.length - 1)}
            onMouseEnter={() => setActive(options.length - 1)}
            className={cn(
              "mt-1 cursor-pointer border-t border-navy-3 px-3 pt-2 text-gold",
              active === options.length - 1 && "bg-navy-3",
            )}
          >
            Ver todos os resultados para “{term}”
          </div>
        ) : null}
      </div>
    </>
  );
}

function Option({
  id,
  hit,
  active,
  position,
  onSelect,
  onHover,
}: {
  id: string;
  hit: AssetHit;
  active: boolean;
  position: number;
  onSelect: (index: number) => void;
  onHover: (index: number) => void;
}) {
  const isSecurity = !["index", "treasury", "crypto"].includes(hit.type);
  return (
    <div
      id={id}
      role="option"
      aria-selected={active}
      onClick={() => onSelect(position)}
      onMouseEnter={() => onHover(position)}
      className={cn(
        "flex cursor-pointer items-baseline gap-3 px-3 py-1.5",
        active && "bg-navy-3",
      )}
    >
      {isSecurity ? <span className="w-16 shrink-0 font-medium tabular-nums">{hit.code}</span> : null}
      <span className="truncate text-ice-70">{hit.name}</span>
    </div>
  );
}
