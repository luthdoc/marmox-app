import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import type { AppRouterInstance } from "next/dist/shared/lib/app-router-context.shared-runtime";

const mockSignIn = vi.hoisted(() => vi.fn());

vi.mock("@/lib/supabase", () => ({
  createClient: () => ({
    auth: {
      signInWithPassword: mockSignIn,
    },
  }),
}));

vi.mock("next/navigation", () => ({
  useRouter: vi.fn(() => ({ push: vi.fn() })),
}));

import { LoginForm } from "../LoginForm";
import { useRouter } from "next/navigation";

describe("LoginForm", () => {
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
    mockSignIn.mockReset();
  });

  it("renderiza campos de email, senha e botao Entrar", () => {
    render(<LoginForm />);
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/senha/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /entrar/i })).toBeInTheDocument();
  });

  it("botao Entrar e do tipo primary (pill, action-blue)", () => {
    render(<LoginForm />);
    const btn = screen.getByRole("button", { name: /entrar/i });
    expect(btn.className).toMatch(/rounded-\[9999px\]|rounded-full/);
    expect(btn.className).toContain("bg-action-blue");
  });

  it("exibe erro inline se email invalido ao submeter", async () => {
    render(<LoginForm />);
    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: "nao-e-email" },
    });
    fireEvent.change(screen.getByLabelText(/senha/i), {
      target: { value: "senha123" },
    });
    fireEvent.click(screen.getByRole("button", { name: /entrar/i }));

    await waitFor(() => {
      expect(screen.getByText(/email.*inválido|inválido.*email/i)).toBeInTheDocument();
    });
    expect(mockSignIn).not.toHaveBeenCalled();
  });

  it("exibe erro inline se senha vazia ao submeter", async () => {
    render(<LoginForm />);
    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: "user@example.com" },
    });
    fireEvent.click(screen.getByRole("button", { name: /entrar/i }));

    await waitFor(() => {
      expect(screen.getByText(/senha.*obrigatória|obrigatória/i)).toBeInTheDocument();
    });
    expect(mockSignIn).not.toHaveBeenCalled();
  });

  it("chama signInWithPassword com email e senha ao submeter formulario valido", async () => {
    mockSignIn.mockResolvedValue({ data: { session: { access_token: "tok" } }, error: null });

    render(<LoginForm />);
    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: "owner@marmax.com" },
    });
    fireEvent.change(screen.getByLabelText(/senha/i), {
      target: { value: "senha123" },
    });
    fireEvent.click(screen.getByRole("button", { name: /entrar/i }));

    await waitFor(() => {
      expect(mockSignIn).toHaveBeenCalledWith({
        email: "owner@marmax.com",
        password: "senha123",
      });
    });
  });

  it("redireciona para /dashboard apos login bem-sucedido", async () => {
    mockSignIn.mockResolvedValue({ data: { session: { access_token: "tok" } }, error: null });

    render(<LoginForm />);
    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: "owner@marmax.com" },
    });
    fireEvent.change(screen.getByLabelText(/senha/i), {
      target: { value: "senha123" },
    });
    fireEvent.click(screen.getByRole("button", { name: /entrar/i }));

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/dashboard");
    });
  });

  it("exibe mensagem de erro generica sem detalhes internos quando Supabase retorna erro", async () => {
    mockSignIn.mockResolvedValue({
      data: { user: null, session: null },
      error: { message: "Invalid login credentials", status: 400, __isAuthError: true },
    });

    render(<LoginForm />);
    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: "owner@marmax.com" },
    });
    fireEvent.change(screen.getByLabelText(/senha/i), {
      target: { value: "senhaerrada" },
    });
    fireEvent.click(screen.getByRole("button", { name: /entrar/i }));

    await waitFor(() => {
      const errorMsg = screen.getByRole("alert");
      expect(errorMsg).toBeInTheDocument();
      expect(errorMsg.textContent).not.toContain("Invalid login credentials");
    });
    expect(mockPush).not.toHaveBeenCalled();
  });
});
