"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { EVENT_CLASSES, EVENT_GROUPS, parseFilter } from "@/lib/agenda";
import { track } from "@/lib/umami";
import { cn } from "@/lib/cn";

// Filtros da `/agenda` por tipo e por classe (plano 4.3), com o estado na URL
// (`?tipo=proventos,macro&classe=fiis`).
//
// A página da semana é estática (ISR) e traz **todos** os eventos; o filtro só esconde
// o que não foi escolhido, por CSS, a partir dos `data-grupo`/`data-classe` de cada
// item. Trocar de filtro não pede nada ao servidor e a URL continua compartilhável.
// Evento macro não é de classe nenhuma: o filtro de classe não o esconde (quem não quer
// macro desmarca o tipo).

const GROUPS = EVENT_GROUPS.map((g) => g.slug);
const CLASSES = EVENT_CLASSES.map((c) => c.slug);

type Props = { classes?: boolean };

export function AgendaFilters(props: Props) {
  return (
    <Suspense fallback={<Chips {...props} tipos={[]} classes_={[]} />}>
      <LiveFilters {...props} />
    </Suspense>
  );
}

function LiveFilters(props: Props) {
  const params = useSearchParams();
  const tipos = parseFilter(params.get("tipo"), GROUPS);
  const classes = parseFilter(params.get("classe"), CLASSES);

  function toggle(param: "tipo" | "classe", value: string, current: string[]) {
    const next = current.includes(value) ? current.filter((v) => v !== value) : [...current, value];
    const url = new URL(window.location.href);
    if (next.length) url.searchParams.set(param, next.join(","));
    else url.searchParams.delete(param);
    window.history.replaceState(null, "", url);
    track("agenda_filter", { filter: param, value, on: next.includes(value) });
  }

  const rules: string[] = [];
  if (tipos.length) {
    rules.push(`[data-agenda] [data-grupo]:not(${tipos.map((t) => `[data-grupo="${t}"]`).join(",")}){display:none}`);
  }
  if (classes.length) {
    rules.push(
      `[data-agenda] [data-classe]:not([data-classe="macro"]):not(${classes.map((c) => `[data-classe="${c}"]`).join(",")}){display:none}`,
    );
  }

  return (
    <>
      {rules.length ? <style>{rules.join("\n")}</style> : null}
      <Chips {...props} tipos={tipos} classes_={classes} onToggle={toggle} />
    </>
  );
}

function Chips({
  classes: showClasses = true,
  tipos,
  classes_,
  onToggle,
}: Props & {
  tipos: string[];
  classes_: string[];
  onToggle?: (param: "tipo" | "classe", value: string, current: string[]) => void;
}) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:gap-8">
      <Group
        label="Tipo"
        items={EVENT_GROUPS.map((g) => ({ value: g.slug, label: g.label }))}
        selected={tipos}
        onToggle={onToggle ? (value) => onToggle("tipo", value, tipos) : undefined}
      />
      {showClasses ? (
        <Group
          label="Classe"
          items={EVENT_CLASSES.map((c) => ({ value: c.slug, label: c.label }))}
          selected={classes_}
          onToggle={onToggle ? (value) => onToggle("classe", value, classes_) : undefined}
        />
      ) : null}
    </div>
  );
}

function Group({
  label,
  items,
  selected,
  onToggle,
}: {
  label: string;
  items: { value: string; label: string }[];
  selected: string[];
  onToggle?: (value: string) => void;
}) {
  return (
    <fieldset className="flex flex-wrap items-center gap-2">
      <legend className="float-left mr-2 text-table text-ice-70">{label}:</legend>
      {items.map((item) => {
        const on = selected.includes(item.value);
        return (
          <button
            key={item.value}
            type="button"
            aria-pressed={on}
            disabled={!onToggle}
            onClick={() => onToggle?.(item.value)}
            className={cn(
              "rounded-full border px-3 py-1 text-table transition-colors",
              on ? "border-gold text-gold" : "border-navy-3 text-ice-70 hover:border-gold hover:text-ice",
            )}
          >
            {item.label}
          </button>
        );
      })}
      {selected.length === 0 ? <span className="text-xs text-ice-70">(todos)</span> : null}
    </fieldset>
  );
}
