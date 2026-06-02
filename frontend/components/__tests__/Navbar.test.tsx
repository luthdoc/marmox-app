import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import type { AppRouterInstance } from "next/dist/shared/lib/app-router-context.shared-runtime";

const mockSignOut = vi.hoisted(() => vi.fn());

vi.mock("@/lib/supabase", () => ({
  createClient: () => ({
    auth: {
      signOut: mockSignOut,
    },
  }),
}));

vi.mock("next/navigation", () => ({
  useRouter: vi.fn(),
}));

import { Navbar } from "../Navbar";
import { useRouter } from "next/navigation";

describe("Navbar", () => {
  let mockPush: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    mockPush = vi.fn();
    vi.mocked(useRouter).mockReturnValue({
      push: mockPush,
      back: vi.fn(),
      forward: vi.fn(),
      refresh: vi.fn(),
      replace: vi.fn(),
      prefetch: vi.fn(),
    } as unknown as AppRouterInstance);
    mockSignOut.mockReset();
  });

  it("exibe o nome Marmax", () => {
    render(<Navbar />);
    expect(screen.getByText("Marmax")).toBeInTheDocument();
  });

  it("exibe botao Sair", () => {
    render(<Navbar />);
    expect(screen.getByRole("button", { name: /sair/i })).toBeInTheDocument();
  });

  it("botao Sair nao tem sombra", () => {
    render(<Navbar />);
    const btn = screen.getByRole("button", { name: /sair/i });
    expect(btn.className).not.toMatch(/shadow/);
  });

  it("clicar em Sair chama signOut e redireciona para /login", async () => {
    mockSignOut.mockResolvedValue({ error: null });
    render(<Navbar />);
    fireEvent.click(screen.getByRole("button", { name: /sair/i }));

    await waitFor(() => {
      expect(mockSignOut).toHaveBeenCalled();
      expect(mockPush).toHaveBeenCalledWith("/login");
    });
  });
});
