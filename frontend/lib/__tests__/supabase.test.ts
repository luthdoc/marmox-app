import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock @supabase/ssr before imports
vi.mock("@supabase/ssr", () => ({
  createBrowserClient: vi.fn(() => ({
    auth: { getSession: vi.fn() },
  })),
}));

describe("supabase browser client", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  it("exporta um objeto supabase com auth", async () => {
    const { createBrowserClient } = await import("@supabase/ssr");
    const mockClient = { auth: { getSession: vi.fn() } };
    vi.mocked(createBrowserClient).mockReturnValue(mockClient as ReturnType<typeof createBrowserClient>);

    const { supabase } = await import("../supabase");
    expect(supabase).toBeDefined();
    expect(supabase.auth).toBeDefined();
  });

  it("usa NEXT_PUBLIC_SUPABASE_URL e NEXT_PUBLIC_SUPABASE_ANON_KEY", async () => {
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "https://test.supabase.co");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "test-anon-key");

    const { createBrowserClient } = await import("@supabase/ssr");
    await import("../supabase");

    expect(createBrowserClient).toHaveBeenCalledWith(
      "https://test.supabase.co",
      "test-anon-key"
    );
  });
});
