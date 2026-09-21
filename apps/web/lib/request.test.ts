import { describe, expect, it } from "vitest";
import { clientIp, isSameOrigin } from "./request";

const h = (init: Record<string, string>) => new Headers(init);

describe("clientIp", () => {
  it("prefere cf-connecting-ip, depois x-real-ip, depois o primeiro x-forwarded-for", () => {
    expect(clientIp(h({ "cf-connecting-ip": "1.1.1.1", "x-real-ip": "2.2.2.2" }))).toBe("1.1.1.1");
    expect(clientIp(h({ "x-real-ip": "2.2.2.2", "x-forwarded-for": "3.3.3.3, 4.4.4.4" }))).toBe("2.2.2.2");
    expect(clientIp(h({ "x-forwarded-for": "3.3.3.3, 4.4.4.4" }))).toBe("3.3.3.3");
    expect(clientIp(h({}))).toBe("0.0.0.0");
  });
});

describe("isSameOrigin", () => {
  it("aceita o próprio site (SITE_URL de teste = http://localhost:3000)", () => {
    expect(isSameOrigin(h({ origin: "http://localhost:3000" }))).toBe(true);
    expect(isSameOrigin(h({ "sec-fetch-site": "same-origin" }))).toBe(true);
  });

  it("rejeita outra origem, cross-site e ausência de ambos", () => {
    expect(isSameOrigin(h({ origin: "https://evil.example" }))).toBe(false);
    expect(isSameOrigin(h({ origin: "http://localhost:3000", "sec-fetch-site": "cross-site" }))).toBe(false);
    expect(isSameOrigin(h({}))).toBe(false);
    expect(isSameOrigin(h({ origin: "not a url" }))).toBe(false);
  });
});
