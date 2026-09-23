import { createCipheriv, createDecipheriv, createHmac, hkdfSync, randomBytes } from "node:crypto";

// Cifra das colunas financeiras (site.md §7.4): AES-256-GCM na aplicação, chave em env,
// `key_version` na linha. Defesa em profundidade contra dump de banco: sem a chave, uma
// movimentação é só "compra de PETR4 em 12/03", sem quantidade nem preço.
//
// Três escolhas:
// - **Dado autenticado (AAD)** amarra o texto cifrado à tabela e à carteira. Copiar o
//   `payload` de uma linha para a carteira de outra pessoa não decifra — falha na
//   verificação, em vez de mostrar o número de um no painel do outro.
// - **Rotação**: novas gravações usam `APP_ENCRYPTION_KEY_VERSION`; leituras aceitam
//   qualquer `APP_ENCRYPTION_KEY_V<n>` presente, para as linhas antigas continuarem
//   legíveis até serem regravadas.
// - **HMAC para dedupe** (`keyedHash`), com chave derivada (HKDF) e nunca a de cifra.

const IV_BYTES = 12;
const TAG_BYTES = 16;

export type Encrypted = { payload: string; keyVersion: number };

/** De onde vêm as chaves: `process.env` em produção, um dicionário nos testes. */
type KeySource = Record<string, string | undefined>;

function keyFor(version: number, source: KeySource = process.env): Buffer {
  const raw = source[`APP_ENCRYPTION_KEY_V${version}`];
  if (!raw) throw new Error(`chave de cifra APP_ENCRYPTION_KEY_V${version} ausente`);
  const key = Buffer.from(raw, "base64");
  if (key.length !== 32) throw new Error(`APP_ENCRYPTION_KEY_V${version} precisa ter 32 bytes (base64)`);
  return key;
}

function currentVersion(source: KeySource = process.env): number {
  const version = Number(source.APP_ENCRYPTION_KEY_VERSION ?? "1");
  if (!Number.isInteger(version) || version < 1) throw new Error("APP_ENCRYPTION_KEY_VERSION inválida");
  return version;
}

/** Cifra um objeto JSON. `context` vira o dado autenticado ("transactions:<portfolio_id>"). */
export function encryptJson(value: unknown, context: string, source: KeySource = process.env): Encrypted {
  const keyVersion = currentVersion(source);
  const iv = randomBytes(IV_BYTES);
  const cipher = createCipheriv("aes-256-gcm", keyFor(keyVersion, source), iv);
  cipher.setAAD(Buffer.from(context, "utf8"));
  const ciphertext = Buffer.concat([cipher.update(JSON.stringify(value), "utf8"), cipher.final()]);
  const payload = Buffer.concat([iv, cipher.getAuthTag(), ciphertext]).toString("base64");
  return { payload, keyVersion };
}

/** Decifra; lança se o texto foi alterado, se o contexto não bate ou se falta a chave. */
export function decryptJson<T>(encrypted: Encrypted, context: string, source: KeySource = process.env): T {
  const raw = Buffer.from(encrypted.payload, "base64");
  if (raw.length < IV_BYTES + TAG_BYTES) throw new Error("payload cifrado truncado");
  const decipher = createDecipheriv("aes-256-gcm", keyFor(encrypted.keyVersion, source), raw.subarray(0, IV_BYTES));
  decipher.setAAD(Buffer.from(context, "utf8"));
  decipher.setAuthTag(raw.subarray(IV_BYTES, IV_BYTES + TAG_BYTES));
  const plain = Buffer.concat([decipher.update(raw.subarray(IV_BYTES + TAG_BYTES)), decipher.final()]);
  return JSON.parse(plain.toString("utf8")) as T;
}

/**
 * HMAC-SHA256 de campos canônicos, para dedupe de importação (`external_key`).
 * A chave é derivada da de cifra por HKDF com rótulo próprio; o prefixo `k<versão>:`
 * registra qual chave gerou o valor.
 */
export function keyedHash(parts: (string | number)[], source: KeySource = process.env): string {
  const version = currentVersion(source);
  const macKey = Buffer.from(hkdfSync("sha256", keyFor(version, source), Buffer.alloc(0), "alpherion:external_key", 32));
  const mac = createHmac("sha256", macKey).update(parts.map(String).join("|")).digest("hex");
  return `k${version}:${mac}`;
}
