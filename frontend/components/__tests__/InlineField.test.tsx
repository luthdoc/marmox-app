import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { InlineField } from "../InlineField";

describe("InlineField", () => {
  it("exibe o valor inicial em modo de leitura", () => {
    render(
      <InlineField
        label="Nome"
        value="Marmoraria ABC"
        onSave={vi.fn()}
        validate={(v) => (v ? null : "Obrigatório")}
      />
    );
    expect(screen.getByText("Marmoraria ABC")).toBeInTheDocument();
  });

  it("entra em modo de edicao ao clicar no valor", () => {
    render(
      <InlineField
        label="Nome"
        value="Marmoraria ABC"
        onSave={vi.fn()}
        validate={(v) => (v ? null : "Obrigatório")}
      />
    );
    fireEvent.click(screen.getByText("Marmoraria ABC"));
    expect(screen.getByRole("textbox")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Marmoraria ABC")).toBeInTheDocument();
  });

  it("chama onSave com o novo valor ao pressionar Enter", async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    render(
      <InlineField
        label="Nome"
        value="Marmoraria ABC"
        onSave={onSave}
        validate={(v) => (v ? null : "Obrigatório")}
      />
    );
    fireEvent.click(screen.getByText("Marmoraria ABC"));
    const input = screen.getByRole("textbox");
    fireEvent.change(input, { target: { value: "Novo Nome" } });
    fireEvent.keyDown(input, { key: "Enter" });

    await waitFor(() => {
      expect(onSave).toHaveBeenCalledWith("Novo Nome");
    });
  });

  it("chama onSave ao perder foco (blur)", async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    render(
      <InlineField
        label="Nome"
        value="Marmoraria ABC"
        onSave={onSave}
        validate={(v) => (v ? null : "Obrigatório")}
      />
    );
    fireEvent.click(screen.getByText("Marmoraria ABC"));
    const input = screen.getByRole("textbox");
    fireEvent.change(input, { target: { value: "Novo Nome" } });
    fireEvent.blur(input);

    await waitFor(() => {
      expect(onSave).toHaveBeenCalledWith("Novo Nome");
    });
  });

  it("exibe erro de validacao sem chamar onSave quando campo invalido", async () => {
    const onSave = vi.fn();
    render(
      <InlineField
        label="Nome"
        value="Marmoraria ABC"
        onSave={onSave}
        validate={(v) => (v.trim() ? null : "Obrigatório")}
      />
    );
    fireEvent.click(screen.getByText("Marmoraria ABC"));
    const input = screen.getByRole("textbox");
    fireEvent.change(input, { target: { value: "" } });
    fireEvent.blur(input);

    await waitFor(() => {
      expect(screen.getByText("Obrigatório")).toBeInTheDocument();
    });
    expect(onSave).not.toHaveBeenCalled();
  });

  it("exibe 'Salvo' brevemente apos salvar com sucesso", async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    render(
      <InlineField
        label="Nome"
        value="Marmoraria ABC"
        onSave={onSave}
        validate={(v) => (v ? null : "Obrigatório")}
      />
    );
    fireEvent.click(screen.getByText("Marmoraria ABC"));
    const input = screen.getByRole("textbox");
    fireEvent.change(input, { target: { value: "Novo Nome" } });
    fireEvent.keyDown(input, { key: "Enter" });

    await waitFor(() => {
      expect(screen.getByText(/salvo/i)).toBeInTheDocument();
    });
  });
});
