import { z } from "zod";
import { assetClass, marketRef } from "@/drizzle/schema";

// Entrada manual (plano 5.3): regras puras, testáveis sem banco.

/** "1.234,56", "38,5" ou "38.5" → "1234.56". Inválido → null. */
export function parseDecimalInput(raw: string | null | undefined): string | null {
  if (raw === null || raw === undefined) return null;
  let text = raw.trim().replace(/\s|R\$/g, "");
  if (text === "") return null;
  if (text.includes(",")) text = text.replace(/\./g, "").replace(",", ".");
  else if ((text.match(/\./g) ?? []).length > 1) text = text.replace(/\./g, "");
  return /^\d{1,15}(\.\d{1,10})?$/.test(text) ? text : null;
}

const decimalInput = z
  .string()
  .transform((value, ctx) => {
    const parsed = parseDecimalInput(value);
    if (parsed === null) {
      ctx.addIssue({ code: "custom", message: "número inválido" });
      return z.NEVER;
    }
    return parsed;
  });

export const manualTransactionSchema = z.object({
  asset: z.object({
    symbol: z.string().trim().min(1).max(80),
    name: z.string().trim().min(1).max(200),
    asset_class: z.enum(assetClass.enumValues),
    market_ref: z.enum(marketRef.enumValues),
  }),
  date: z
    .string()
    .regex(/^\d{4}-\d{2}-\d{2}$/)
    .refine((d) => d <= new Date().toISOString().slice(0, 10), "data no futuro"),
  side: z.enum(["buy", "sell"]),
  quantity: decimalInput.refine((v) => Number(v) > 0, "quantidade precisa ser maior que zero"),
  price: decimalInput,
  fees: decimalInput.optional().default("0"),
  note: z.string().trim().max(200).optional(),
});
