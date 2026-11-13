import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
import { POST } from "@/app/api/auth/login/route";
import { ACCESS_KEY_COOKIE, verifySessionToken } from "@/lib/auth/session";

function makeLoginRequest(body: unknown): NextRequest {
  return new NextRequest("http://localhost/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

describe("POST /api/auth/login", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("returns 503 when no auth is configured", async () => {
    vi.stubEnv("AUTH_USERNAME", "");
    vi.stubEnv("AUTH_PASSWORD", "");
    vi.stubEnv("HINDSIGHT_CP_ACCESS_KEY", "");
    vi.stubEnv("AUTH_SECRET_KEY", "");

    const res = await POST(makeLoginRequest({ username: "admin", password: "pwd" }));
    expect(res.status).toBe(503);
  });

  it("authenticates via username and password when AUTH_USERNAME and AUTH_PASSWORD configured", async () => {
    vi.stubEnv("AUTH_USERNAME", "admin");
    vi.stubEnv("AUTH_PASSWORD", "secret123");

    // Invalid credentials -> 401
    const failRes = await POST(makeLoginRequest({ username: "admin", password: "wrong" }));
    expect(failRes.status).toBe(401);

    // Valid credentials -> 200 with session cookie
    const okRes = await POST(makeLoginRequest({ username: "admin", password: "secret123" }));
    expect(okRes.status).toBe(200);

    const cookie = okRes.cookies.get(ACCESS_KEY_COOKIE);
    expect(cookie?.value).toBeDefined();
    expect(await verifySessionToken(cookie?.value, "secret123")).toBe(true);
  });

  it("authenticates via access key when HINDSIGHT_CP_ACCESS_KEY configured", async () => {
    vi.stubEnv("HINDSIGHT_CP_ACCESS_KEY", "access-token-999");

    const failRes = await POST(makeLoginRequest({ key: "wrong-key" }));
    expect(failRes.status).toBe(401);

    const okRes = await POST(makeLoginRequest({ key: "access-token-999" }));
    expect(okRes.status).toBe(200);

    const cookie = okRes.cookies.get(ACCESS_KEY_COOKIE);
    expect(cookie?.value).toBeDefined();
    expect(await verifySessionToken(cookie?.value, "access-token-999")).toBe(true);
  });
});
