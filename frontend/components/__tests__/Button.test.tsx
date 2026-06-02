import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { Button } from "../ui/Button";

describe("Button component", () => {
  it("variante primary tem border-radius pill (9999px)", () => {
    render(<Button variant="primary">Salvar</Button>);
    const btn = screen.getByRole("button", { name: "Salvar" });
    expect(btn.className).toMatch(/rounded-\[9999px\]|rounded-full/);
  });

  it("variante primary tem fundo action-blue e texto branco", () => {
    render(<Button variant="primary">Salvar</Button>);
    const btn = screen.getByRole("button", { name: "Salvar" });
    expect(btn.className).toContain("bg-action-blue");
    expect(btn.className).toContain("text-white");
  });

  it("variante utility tem border-radius sm (8px)", () => {
    render(<Button variant="utility">Cancelar</Button>);
    const btn = screen.getByRole("button", { name: "Cancelar" });
    expect(btn.className).toMatch(/rounded-\[8px\]/);
  });

  it("variante utility tem borda hairline sem fundo colorido", () => {
    render(<Button variant="utility">Cancelar</Button>);
    const btn = screen.getByRole("button", { name: "Cancelar" });
    expect(btn.className).toContain("border");
    expect(btn.className).not.toContain("bg-action-blue");
  });

  it("nenhuma variante tem sombra", () => {
    const { rerender } = render(<Button variant="primary">A</Button>);
    const btn = screen.getByRole("button", { name: "A" });
    expect(btn.className).not.toMatch(/shadow/);

    rerender(<Button variant="utility">A</Button>);
    expect(btn.className).not.toMatch(/shadow/);
  });
});
