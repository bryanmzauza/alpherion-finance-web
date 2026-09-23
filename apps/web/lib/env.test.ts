import { describe, expect, it } from "vitest";
import { parseEnv } from "./env";

describe("parseEnv", () => {
  it("aceita um ambiente completo", () => {
    const env = parseEnv({
      APP_ENV: "prod",
      SITE_URL: "https://alpherion.com.br",
      APP_URL: "https://app.alpherion.com.br",
      API_URL: "http://api:8000",
      DATABASE_URL: "postgres://web:x@postgres/alpherion",
      API_SERVICE_TOKEN_WEB: "a".repeat(43),
      BETTER_AUTH_SECRET: "b".repeat(44),
      APP_ENCRYPTION_KEY_V1: "c".repeat(44),
    });
    expect(env.APP_ENV).toBe("prod");
    expect(env.API_URL).toBe("http://api:8000");
  });

  it("segredo de sessão e chave de cifra são obrigatórios em produção", () => {
    const semSegredos = {
      APP_ENV: "prod",
      DATABASE_URL: "postgres://web:x@postgres/alpherion",
      API_SERVICE_TOKEN_WEB: "a".repeat(43),
    };
    expect(() => parseEnv(semSegredos)).toThrow(/BETTER_AUTH_SECRET/);
    expect(() => parseEnv(semSegredos)).toThrow(/APP_ENCRYPTION_KEY_V1/);
    expect(() => parseEnv({ ...semSegredos, APP_ENV: "dev" })).not.toThrow();
  });

  it("rejeita URL inválida com mensagem que aponta a variável", () => {
    expect(() => parseEnv({ SITE_URL: "alpherion" })).toThrow(/SITE_URL/);
  });
});
