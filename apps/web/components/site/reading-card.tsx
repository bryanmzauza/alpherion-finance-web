import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import type { Reading } from "@/content/site";

const STATUS_LABEL: Record<Reading["status"], { label: string; icon: string }> = {
  risk: { label: "atenção alta", icon: "▲" },
  warn: { label: "atenção", icon: "●" },
  ok: { label: "sem alerta", icon: "✓" },
};

// Uma das cinco leituras (landing, seção 2; /raio-x). Semântica de risco = ícone + texto + cor.
export function ReadingCard({ reading, href }: { reading: Reading; href?: string }) {
  const status = STATUS_LABEL[reading.status];
  const body = (
    <>
      <div className="flex items-start justify-between gap-3">
        <p className="text-table text-ice-70">{reading.name}</p>
        <Badge tone={reading.status}>
          <span aria-hidden="true">{status.icon}</span> {status.label}
        </Badge>
      </div>
      <p className="mt-2 font-display text-xl font-semibold">{reading.question}</p>
      <p className="mt-3 text-table text-ice-70">{reading.definition}</p>
      <p className="tabular mt-6 font-display text-4xl font-bold text-gold">{reading.value}</p>
      <p className="mt-1 text-table text-ice-70">{reading.valueLabel}</p>
    </>
  );
  return href ? (
    <Link href={href} className="block rounded-lg transition-colors hover:[&>div]:border-gold/50">
      <Card className="h-full">{body}</Card>
    </Link>
  ) : (
    <Card className="h-full">{body}</Card>
  );
}
