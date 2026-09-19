import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, apiFetch } from "./api-client";

const jsonResponse = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

describe("apiFetch", () => {
  afterEach(() => vi.restoreAllMocks());

  it("envia o token de serviço e monta a URL sobre API_URL", async () => {
    const spy = vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse({ status: "ok" }));
    const data = await apiFetch<{ status: string }>("/v1/health");

    expect(data.status).toBe("ok");
    const [url, init] = spy.mock.calls[0]!;
    expect(url).toBe("http://localhost:8000/v1/health");
    expect((init!.headers as Record<string, string>).Authorization).toBe("Bearer test-token");
  });

  it("serializa body como JSON", async () => {
    const spy = vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse({}));
    await apiFetch("/v1/x", { method: "POST", body: { a: 1 } });
    const init = spy.mock.calls[0]![1]!;
    expect(init.body).toBe('{"a":1}');
    expect((init.headers as Record<string, string>)["Content-Type"]).toBe("application/json");
  });

  it("lança ApiError com o status em resposta não-2xx", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse({ detail: "x" }, 403));
    await expect(apiFetch("/v1/x")).rejects.toMatchObject<Partial<ApiError>>({ status: 403, path: "/v1/x" });
  });
});
