import Link from "next/link";
import { DISCLAIMER_FULL, DISCLAIMER_SHORT } from "@/content/legal/aviso";
import { cn } from "@/lib/cn";

type Props = { variant?: "short" | "full"; className?: string };

export function Disclaimer({ variant = "short", className }: Props) {
  return (
    <aside aria-label="Aviso legal" className={cn("text-table text-ice-70", className)}>
      <p>
        {variant === "full" ? DISCLAIMER_FULL : DISCLAIMER_SHORT}{" "}
        <Link href="/aviso-legal" className="text-gold underline-offset-4 hover:underline">
          Aviso legal completo
        </Link>
        .
      </p>
    </aside>
  );
}
