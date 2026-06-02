import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { LeadRow } from "../LeadRow";

const baseLead = {
  id: "lead-123",
  name: "João Silva",
  phone: "+5511987654321",
  service_type: "Granito",
  status: "new" as const,
  last_contact_at: "2024-03-15T10:30:00.000Z",
};

describe("LeadRow", () => {
  it("exibe o nome do lead", () => {
    render(<LeadRow lead={baseLead} onClick={vi.fn()} />);
    expect(screen.getByText("João Silva")).toBeInTheDocument();
  });

  it("exibe o service_type do lead", () => {
    render(<LeadRow lead={baseLead} onClick={vi.fn()} />);
    expect(screen.getByText("Granito")).toBeInTheDocument();
  });

  it("exibe StatusBadge com status do lead", () => {
    render(<LeadRow lead={baseLead} onClick={vi.fn()} />);
    expect(screen.getByText("new")).toBeInTheDocument();
  });

  it("exibe telefone mascarado quando name e nulo", () => {
    render(
      <LeadRow
        lead={{ ...baseLead, name: null as unknown as string }}
        onClick={vi.fn()}
      />
    );
    // Telefone mascarado deve aparecer com asteriscos
    expect(screen.getByText(/\*{4}/)).toBeInTheDocument();
  });

  it("chama onClick com o id do lead ao clicar na linha", () => {
    const onClick = vi.fn();
    render(<LeadRow lead={baseLead} onClick={onClick} />);
    fireEvent.click(screen.getByRole("row"));
    expect(onClick).toHaveBeenCalledWith("lead-123");
  });
});
