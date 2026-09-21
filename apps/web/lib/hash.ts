import { createHash } from "node:crypto";

/** sha256 em hex de uma string (e-mail normalizado, conteúdo de arquivo). */
export function sha256(input: string | Buffer): string {
  return createHash("sha256").update(input).digest("hex");
}
