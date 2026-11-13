import { describe, expect, it, vi } from "vitest";
import { USER_AGENT, getDataplaneHeaders, lowLevelClient } from "@/lib/hindsight-client";
import { version } from "../../package.json";

describe("dataplane User-Agent", () => {
  it("identifies the control plane and its version", () => {
    expect(USER_AGENT).toBe(`hindsight-control-plane/${version}`);
  });

  it("is sent on direct fetches and by the low-level client", () => {
    expect(getDataplaneHeaders({ "Content-Type": "application/json" })).toMatchObject({
      "User-Agent": USER_AGENT,
      "Content-Type": "application/json",
    });
    const headers = lowLevelClient.getConfig().headers as Headers;
    expect(headers.get("User-Agent")).toBe(USER_AGENT);
  });

  it("authorizes with a bearer token when one is configured", async () => {
    vi.resetModules();
    vi.stubEnv("HINDSIGHT_CP_DATAPLANE_API_KEY", "");
    vi.stubEnv("AUTH_API_KEY", "shared-secret");
    const { getDataplaneHeaders: fresh } = await import("@/lib/hindsight-client");
    expect(fresh()["Authorization"]).toBe("Bearer shared-secret");
    vi.unstubAllEnvs();
  });
});
