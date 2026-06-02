import { describe, it, expect, vi } from "vitest";

const mockGetAll = vi.fn(() => []);
const mockSet = vi.fn();
const mockDelete = vi.fn();

vi.mock("next/headers", () => ({
  cookies: vi.fn(() => ({
    getAll: mockGetAll,
    set: mockSet,
    delete: mockDelete,
  })),
}));

vi.mock("@supabase/ssr", () => ({
  createServerClient: vi.fn(() => ({
    auth: { getUser: vi.fn() },
  })),
}));

describe("supabase server client", () => {
  it("createSupabaseServerClient retorna um client com auth", async () => {
    const { createSupabaseServerClient } = await import("../supabase-server");
    const client = await createSupabaseServerClient();
    expect(client).toBeDefined();
    expect(client.auth).toBeDefined();
  });

  it("createSupabaseServerClient usa createServerClient da lib ssr", async () => {
    const { createServerClient } = await import("@supabase/ssr");
    const { createSupabaseServerClient } = await import("../supabase-server");
    await createSupabaseServerClient();
    expect(createServerClient).toHaveBeenCalled();
  });
});
