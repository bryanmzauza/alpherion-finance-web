import type { HTMLAttributes } from "react";
import { cn } from "@/lib/cn";

type Tone = "neutral" | "gold" | "ok" | "warn" | "risk";

// Semântica de risco sempre acompanha texto (nunca só cor) — quem usa passa o rótulo.
export function Badge({ tone = "neutral", className, ...props }: HTMLAttributes<HTMLSpanElement> & { tone?: Tone }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium",
        tone === "neutral" && "border-navy-3 text-ice-70",
        tone === "gold" && "border-gold/40 text-gold",
        tone === "ok" && "border-ok/40 text-ok",
        tone === "warn" && "border-warn/40 text-warn",
        tone === "risk" && "border-risk/40 text-risk-text",
        className,
      )}
      {...props}
    />
  );
}
