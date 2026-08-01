// @vitest-environment node
import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import { apiGet, apiPost, apiPut, apiDelete } from "../api";

afterEach(() => {
  vi.restoreAllMocks();
});

/** fetch that resolves with a fresh Response each call (body can only be read once). */
function jsonFetch(body: unknown, init: ResponseInit) {
  const text = typeof body === "string" ? body : JSON.stringify(body);
  return vi.fn(() => Promise.resolve(new Response(text, init)));
}

describe("apiGet", () => {
  it("returns parsed JSON on a 200 response", async () => {
    const fetchMock = jsonFetch({ ok: true }, { status: 200, headers: { "Content-Type": "application/json" } });
    vi.spyOn(globalThis, "fetch").mockImplementation(fetchMock as any);
    const result = await apiGet<{ ok: boolean }>("/thing");
    expect(result).toEqual({ ok: true });
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/thing"));
  });

  it("throws the detail message from a JSON error body", async () => {
    const fetchMock = jsonFetch(
      { detail: "not found" },
      { status: 404, statusText: "Not Found", headers: { "Content-Type": "application/json" } },
    );
    vi.spyOn(globalThis, "fetch").mockImplementation(fetchMock as any);
    await expect(apiGet("/missing")).rejects.toThrow("not found");
  });

  it("throws the raw detail when it is a non-string object", async () => {
    const fetchMock = jsonFetch(
      { detail: { field: "bad" } },
      { status: 422, statusText: "Unprocessable", headers: { "Content-Type": "application/json" } },
    );
    vi.spyOn(globalThis, "fetch").mockImplementation(fetchMock as any);
    await expect(apiGet("/x")).rejects.toThrow(/bad/);
  });

  it("throws the status code when the error body is non-JSON", async () => {
    const fetchMock = jsonFetch("plain text error", {
      status: 500,
      statusText: "Server Error",
      headers: { "Content-Type": "text/plain" },
    });
    vi.spyOn(globalThis, "fetch").mockImplementation(fetchMock as any);
    await expect(apiGet("/boom")).rejects.toThrow(/500/);
  });
});

describe("apiPost", () => {
  it("sends JSON and returns parsed JSON", async () => {
    const fetchMock = jsonFetch({ created: 1 }, { status: 201, headers: { "Content-Type": "application/json" } });
    vi.spyOn(globalThis, "fetch").mockImplementation(fetchMock as any);
    const result = await apiPost<{ created: number }>("/things", { name: "a" });
    expect(result).toEqual({ created: 1 });
    const [url, init] = fetchMock.mock.calls[0];
    expect(init.method).toBe("POST");
    expect(init.headers).toMatchObject({ "Content-Type": "application/json" });
    expect(init.body).toBe(JSON.stringify({ name: "a" }));
  });

  it("throws the detail message on a 400 JSON error", async () => {
    const fetchMock = jsonFetch(
      { detail: "invalid" },
      { status: 400, statusText: "Bad Request", headers: { "Content-Type": "application/json" } },
    );
    vi.spyOn(globalThis, "fetch").mockImplementation(fetchMock as any);
    await expect(apiPost("/things", { name: "a" })).rejects.toThrow("invalid");
  });
});

describe("apiPut", () => {
  it("uses PUT and returns parsed JSON", async () => {
    const fetchMock = jsonFetch({ updated: true }, { status: 200, headers: { "Content-Type": "application/json" } });
    vi.spyOn(globalThis, "fetch").mockImplementation(fetchMock as any);
    const result = await apiPut<{ updated: boolean }>("/things/1", { name: "b" });
    expect(result).toEqual({ updated: true });
    expect(fetchMock.mock.calls[0][1].method).toBe("PUT");
  });

  it("throws the detail on error", async () => {
    const fetchMock = jsonFetch(
      { detail: "conflict" },
      { status: 409, statusText: "Conflict", headers: { "Content-Type": "application/json" } },
    );
    vi.spyOn(globalThis, "fetch").mockImplementation(fetchMock as any);
    await expect(apiPut("/things/1", { name: "b" })).rejects.toThrow("conflict");
  });
});

describe("apiDelete", () => {
  it("uses DELETE and returns parsed JSON", async () => {
    const fetchMock = jsonFetch({ deleted: true }, { status: 200, headers: { "Content-Type": "application/json" } });
    vi.spyOn(globalThis, "fetch").mockImplementation(fetchMock as any);
    const result = await apiDelete<{ deleted: boolean }>("/things/1");
    expect(result).toEqual({ deleted: true });
    expect(fetchMock.mock.calls[0][1].method).toBe("DELETE");
  });

  it("throws the detail on error", async () => {
    const fetchMock = jsonFetch(
      { detail: "forbidden" },
      { status: 403, statusText: "Forbidden", headers: { "Content-Type": "application/json" } },
    );
    vi.spyOn(globalThis, "fetch").mockImplementation(fetchMock as any);
    await expect(apiDelete("/things/1")).rejects.toThrow("forbidden");
  });
});
