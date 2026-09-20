import type { ReactNode } from "react";

// Regra da palavra dourada (§5): no máximo UM <Gold> por título.
export function Gold({ children }: { children: ReactNode }) {
  return <span className="text-gold">{children}</span>;
}
