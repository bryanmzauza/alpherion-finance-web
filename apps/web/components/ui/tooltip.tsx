"use client";

import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { cn } from "@/lib/cn";

type Props = {
  /** Definição do termo (uma frase). */
  content: ReactNode;
  /** O termo em si; vira um botão acessível. */
  children: ReactNode;
  className?: string;
};

// Definição de termo técnico (§1: "todo termo é definido na primeira vez").
// Abre por hover, foco ou toque; fecha com Esc ou clique fora. Sem biblioteca.
export function Tooltip({ content, children, className }: Props) {
  const id = useId();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("mousedown", onClick);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("mousedown", onClick);
    };
  }, [open]);

  return (
    <span ref={ref} className={cn("relative inline-block", className)}>
      <button
        type="button"
        aria-describedby={id}
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        className="cursor-help border-b border-dotted border-ice-70 text-inherit"
      >
        {children}
      </button>
      <span
        id={id}
        role="tooltip"
        className={cn(
          "absolute left-1/2 z-20 mt-2 w-64 -translate-x-1/2 rounded-md border border-navy-3 bg-navy-2 p-3 text-left text-table text-ice shadow-lg",
          open ? "block" : "hidden",
        )}
      >
        {content}
      </span>
    </span>
  );
}
