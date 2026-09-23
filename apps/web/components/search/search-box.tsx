"use client";

import { lazy, Suspense, useId, useRef, useState } from "react";
import { MAX_QUERY } from "@/lib/asset-search";
import { track } from "@/lib/umami";
import { cn } from "@/lib/cn";

// Busca global do header (site.md §2.1, plano 4.1).
//
// Esta casca é tudo o que entra no JS inicial da página: um `<form>` que funciona sem
// JavaScript (Enter → `/busca?q=`) e o `<input>` com os atributos de combobox. A parte
// pesada — requisição, teclado, lista de resultados — está em `search-results.tsx` e só
// é baixada no **primeiro foco** do campo. A landing não paga pela busca de quem não
// busca.
//
// O `<input>` é um só do começo ao fim: carregar o módulo não troca o elemento, então
// nem o foco nem o que já foi digitado se perdem.

const SearchResults = lazy(() => import("./search-results"));

export type ComboboxState = { open: boolean; activeId: string | null };

type Props = {
  /** `lg` é a versão em destaque de `/mercado` e da página 404. */
  size?: "sm" | "lg";
  className?: string;
  defaultValue?: string;
};

export function SearchBox({ size = "sm", className, defaultValue = "" }: Props) {
  const id = useId();
  const inputId = `${id}-q`;
  const listId = `${id}-resultados`;
  const inputRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState(defaultValue);
  const [loaded, setLoaded] = useState(false);
  const [combobox, setCombobox] = useState<ComboboxState>({ open: false, activeId: null });
  const opened = useRef(false);

  // Passar o mouse já adianta o download; o evento `search_open` conta só o foco,
  // que é quem de fato abriu a busca.
  function load() {
    setLoaded(true);
  }

  function open() {
    load();
    if (!opened.current) {
      opened.current = true;
      track("search_open");
    }
  }

  return (
    <form action="/busca" method="get" role="search" className={cn("relative", className)}>
      <label htmlFor={inputId} className="sr-only">
        Buscar ação, FII, ETF, BDR, índice, título do Tesouro ou cripto
      </label>
      <input
        ref={inputRef}
        id={inputId}
        name="q"
        type="search"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        onFocus={open}
        onPointerEnter={load}
        maxLength={MAX_QUERY}
        autoComplete="off"
        autoCorrect="off"
        spellCheck={false}
        enterKeyHint="search"
        placeholder={size === "lg" ? "Busque por ticker, empresa, índice ou cripto" : "Buscar ativo"}
        role="combobox"
        aria-autocomplete="list"
        aria-expanded={combobox.open}
        aria-controls={loaded ? listId : undefined}
        aria-activedescendant={combobox.activeId ?? undefined}
        className={cn(
          "w-full rounded-md border border-navy-3 bg-navy-2 text-ice placeholder:text-ice-70 focus:border-gold focus:outline-none",
          size === "lg" ? "h-12 px-4 text-body" : "h-9 px-3 text-table",
        )}
      />
      {loaded ? (
        <Suspense fallback={null}>
          <SearchResults
            query={query}
            inputRef={inputRef}
            listId={listId}
            onStateChange={setCombobox}
          />
        </Suspense>
      ) : null}
    </form>
  );
}
