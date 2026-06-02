import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { ConversationView } from "../ConversationView";

const messages = [
  {
    id: "msg-1",
    content: "Oi, quero um granito para minha cozinha",
    direction: "inbound" as const,
    created_at: "2024-03-15T10:00:00.000Z",
    media_url: null,
  },
  {
    id: "msg-2",
    content: "Claro! Qual tamanho você precisa?",
    direction: "outbound" as const,
    created_at: "2024-03-15T10:01:00.000Z",
    media_url: null,
  },
  {
    id: "msg-3",
    content: "Foto do local",
    direction: "inbound" as const,
    created_at: "2024-03-15T10:02:00.000Z",
    media_url: "https://example.com/foto.jpg",
  },
];

describe("ConversationView", () => {
  it("exibe o conteudo de cada mensagem", () => {
    render(<ConversationView messages={messages} />);
    expect(screen.getByText("Oi, quero um granito para minha cozinha")).toBeInTheDocument();
    expect(screen.getByText("Claro! Qual tamanho você precisa?")).toBeInTheDocument();
  });

  it("mensagem inbound tem alinhamento a esquerda", () => {
    const { container } = render(<ConversationView messages={[messages[0]]} />);
    const msgEl = container.querySelector("[data-direction='inbound']");
    expect(msgEl).not.toBeNull();
    expect(msgEl!.className).toMatch(/self-start|items-start|justify-start|text-left|mr-auto/);
  });

  it("mensagem outbound tem alinhamento a direita", () => {
    const { container } = render(<ConversationView messages={[messages[1]]} />);
    const msgEl = container.querySelector("[data-direction='outbound']");
    expect(msgEl).not.toBeNull();
    expect(msgEl!.className).toMatch(/self-end|items-end|justify-end|text-right|ml-auto/);
  });

  it("exibe link 'Ver mídia' para mensagem com media_url", () => {
    render(<ConversationView messages={[messages[2]]} />);
    const link = screen.getByRole("link", { name: /ver mídia/i });
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute("href", "https://example.com/foto.jpg");
    expect(link).toHaveAttribute("target", "_blank");
  });

  it("nao exibe link de midia para mensagem sem media_url", () => {
    render(<ConversationView messages={[messages[0]]} />);
    expect(screen.queryByRole("link", { name: /ver mídia/i })).toBeNull();
  });

  it("exibe mensagem de conversa vazia quando sem mensagens", () => {
    render(<ConversationView messages={[]} />);
    expect(screen.getByText(/sem mensagens/i)).toBeInTheDocument();
  });
});
