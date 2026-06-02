import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { LeadDetails } from "../LeadDetails";

const lead = {
  id: "lead-123",
  name: "Maria Souza",
  phone: "+5511987654321",
  service_type: "Granito",
  material: "Granito Preto",
  urgency: "alta",
  neighborhood: "Moema",
  status: "qualified" as const,
  last_contact_at: "2024-03-15T10:30:00.000Z",
};

describe("LeadDetails", () => {
  it("exibe o nome do lead", () => {
    render(<LeadDetails lead={lead} />);
    expect(screen.getByText("Maria Souza")).toBeInTheDocument();
  });

  it("exibe telefone mascarado", () => {
    render(<LeadDetails lead={lead} />);
    expect(screen.getByText(/\*{4}/)).toBeInTheDocument();
  });

  it("exibe o service_type", () => {
    render(<LeadDetails lead={lead} />);
    expect(screen.getByText("Granito")).toBeInTheDocument();
  });

  it("exibe o material", () => {
    render(<LeadDetails lead={lead} />);
    expect(screen.getByText("Granito Preto")).toBeInTheDocument();
  });

  it("exibe o status via StatusBadge", () => {
    render(<LeadDetails lead={lead} />);
    expect(screen.getByText("qualified")).toBeInTheDocument();
  });

  it("exibe o bairro", () => {
    render(<LeadDetails lead={lead} />);
    expect(screen.getByText("Moema")).toBeInTheDocument();
  });
});
