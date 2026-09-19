import { z } from "zod";

// Schemas zod compartilhados. Limites do §7.4 (símbolo ≤ 20 chars, posições ≤ 100 etc.)
// entram aqui conforme as etapas; nada de validar "à mão" nos route handlers.
export { z };

export const ticker = z
  .string()
  .trim()
  .min(1)
  .max(20)
  .regex(/^[A-Za-z0-9.-]+$/, "Símbolo inválido")
  .transform((s) => s.toUpperCase());
