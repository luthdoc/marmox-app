import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { Card } from "../ui/Card";

describe("Card component", () => {
  it("renderiza conteudo filho", () => {
    render(<Card>Conteudo do card</Card>);
    expect(screen.getByText("Conteudo do card")).toBeInTheDocument();
  });

  it("tem border-radius 18px", () => {
    const { container } = render(<Card>Conteudo</Card>);
    const card = container.firstElementChild as HTMLElement;
    expect(card.className).toMatch(/rounded-\[18px\]/);
  });

  it("nao tem sombra", () => {
    const { container } = render(<Card>Conteudo</Card>);
    const card = container.firstElementChild as HTMLElement;
    expect(card.className).not.toMatch(/shadow/);
  });
});
