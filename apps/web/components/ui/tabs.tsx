"use client";

import { useId, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { cn } from "@/lib/cn";

// Abas acessíveis (padrão WAI-ARIA: setas trocam de aba, Home/End vão às pontas).
//
// O conteúdo de **todas** as abas vem renderizado do servidor (a troca é instantânea e
// não pede nada à rede); a escondida usa `hidden`. Mostrar todas antes da hidratação
// faria a página pular quando o JS chega (CLS), então quem usa abas deve garantir que o
// conteúdo das outras também exista numa página própria — em `/mercado`, os eventos
// estão na `/agenda`.
export function Tabs({ tabs }: { tabs: { id: string; label: string; content: ReactNode }[] }) {
  const base = useId();
  const [active, setActive] = useState(0);
  const refs = useRef<(HTMLButtonElement | null)[]>([]);

  function onKeyDown(event: KeyboardEvent<HTMLButtonElement>) {
    const last = tabs.length - 1;
    const next =
      event.key === "ArrowRight"
        ? (active + 1) % tabs.length
        : event.key === "ArrowLeft"
          ? (active - 1 + tabs.length) % tabs.length
          : event.key === "Home"
            ? 0
            : event.key === "End"
              ? last
              : null;
    if (next === null) return;
    event.preventDefault();
    setActive(next);
    refs.current[next]?.focus();
  }

  return (
    <div>
      <div role="tablist" aria-label="Seções do portal" className="flex gap-2 border-b border-navy-3">
        {tabs.map((tab, index) => (
          <button
            key={tab.id}
            ref={(el) => {
              refs.current[index] = el;
            }}
            type="button"
            role="tab"
            id={`${base}-${tab.id}-tab`}
            aria-controls={`${base}-${tab.id}`}
            aria-selected={index === active}
            tabIndex={index === active ? 0 : -1}
            onClick={() => setActive(index)}
            onKeyDown={onKeyDown}
            className={cn(
              "-mb-px border-b-2 px-4 py-2 text-table font-medium",
              index === active ? "border-gold text-ice" : "border-transparent text-ice-70 hover:text-ice",
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>
      {tabs.map((tab, index) => (
        <div
          key={tab.id}
          role="tabpanel"
          id={`${base}-${tab.id}`}
          aria-labelledby={`${base}-${tab.id}-tab`}
          hidden={index !== active}
          tabIndex={0}
          className="pt-8"
        >
          {tab.content}
        </div>
      ))}
    </div>
  );
}
