import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import Home from "../page";

describe("Home page", () => {
  it("exibe o nome da aplicação Marmax", () => {
    render(<Home />);
    expect(screen.getByText("Marmax")).toBeInTheDocument();
  });

  it("aplica classe font-sans ao elemento com o nome da aplicação", () => {
    render(<Home />);
    const el = screen.getByText("Marmax");
    expect(el.className).toContain("font-sans");
  });

  it("aplica tamanho de fonte 17px ao elemento com o nome da aplicação", () => {
    render(<Home />);
    const el = screen.getByText("Marmax");
    expect(el.className).toContain("text-[17px]");
  });
});
