import { randomBytes } from "node:crypto";
import { describe, expect, it } from "vitest";
import { decryptJson, encryptJson, keyedHash } from "@/lib/crypto";

const chave = () => randomBytes(32).toString("base64");
const V1 = chave();
const V2 = chave();
const env1 = { APP_ENCRYPTION_KEY_V1: V1, APP_ENCRYPTION_KEY_VERSION: "1" };
const env2 = { ...env1, APP_ENCRYPTION_KEY_V2: V2, APP_ENCRYPTION_KEY_VERSION: "2" };

const CONTEXTO = "transactions:3f1c6c1e-0000-4000-8000-000000000001";

describe("cifra das colunas financeiras", () => {
  it("ida e volta, sem o número em claro no texto cifrado", () => {
    const linha = { quantity: "100", price: "38.52", fees: "4.90" };
    const cifrado = encryptJson(linha, CONTEXTO, env1);
    expect(cifrado.keyVersion).toBe(1);
    expect(cifrado.payload).not.toContain("38.52");
    expect(decryptJson(cifrado, CONTEXTO, env1)).toEqual(linha);
  });

  it("o mesmo valor cifrado duas vezes dá textos diferentes (IV aleatório)", () => {
    expect(encryptJson({ a: 1 }, CONTEXTO, env1).payload).not.toBe(encryptJson({ a: 1 }, CONTEXTO, env1).payload);
  });

  it("texto adulterado não decifra", () => {
    const cifrado = encryptJson({ quantity: "100" }, CONTEXTO, env1);
    const bytes = Buffer.from(cifrado.payload, "base64");
    bytes[bytes.length - 1] ^= 1;
    expect(() => decryptJson({ ...cifrado, payload: bytes.toString("base64") }, CONTEXTO, env1)).toThrow();
  });

  it("payload copiado para a carteira de outra pessoa não decifra", () => {
    const cifrado = encryptJson({ quantity: "100" }, CONTEXTO, env1);
    expect(() => decryptJson(cifrado, "transactions:outra-carteira", env1)).toThrow();
  });

  it("depois da rotação, grava com a chave nova e ainda lê a antiga", () => {
    const antigo = encryptJson({ quantity: "1" }, CONTEXTO, env1);
    const novo = encryptJson({ quantity: "2" }, CONTEXTO, env2);
    expect(novo.keyVersion).toBe(2);
    expect(decryptJson(antigo, CONTEXTO, env2)).toEqual({ quantity: "1" });
  });

  it("chave ausente ou de tamanho errado é erro explícito", () => {
    expect(() => encryptJson({}, CONTEXTO, {})).toThrow(/APP_ENCRYPTION_KEY_V1/);
    expect(() =>
      encryptJson({}, CONTEXTO, { APP_ENCRYPTION_KEY_V1: Buffer.from("curta").toString("base64") }),
    ).toThrow(/32 bytes/);
  });
});

describe("HMAC do dedupe", () => {
  it("é determinístico e não é o sha256 simples dos campos", () => {
    const partes = ["PETR4", "2026-03-12", "buy", "100", "38.52"];
    expect(keyedHash(partes, env1)).toBe(keyedHash(partes, env1));
    expect(keyedHash(partes, env1)).toMatch(/^k1:[0-9a-f]{64}$/);
    expect(keyedHash([...partes.slice(0, 4), "38.53"], env1)).not.toBe(keyedHash(partes, env1));
  });

  it("muda com a chave (quem tem o banco sem a chave não recalcula)", () => {
    const partes = ["PETR4", "2026-03-12", "buy", "100", "38.52"];
    const outra = { APP_ENCRYPTION_KEY_V1: chave(), APP_ENCRYPTION_KEY_VERSION: "1" };
    expect(keyedHash(partes, outra)).not.toBe(keyedHash(partes, env1));
  });
});
