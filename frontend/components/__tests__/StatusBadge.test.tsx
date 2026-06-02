import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { StatusBadge } from "../ui/StatusBadge";

describe("StatusBadge component", () => {
  it("renderiza o texto do status 'new'", () => {
    render(<StatusBadge status="new" />);
    expect(screen.getByText(/new/i)).toBeInTheDocument();
  });

  it("renderiza o texto do status 'qualified'", () => {
    render(<StatusBadge status="qualified" />);
    expect(screen.getByText(/qualified/i)).toBeInTheDocument();
  });

  it("renderiza o texto do status 'cold'", () => {
    render(<StatusBadge status="cold" />);
    expect(screen.getByText(/cold/i)).toBeInTheDocument();
  });

  it("renderiza o texto do status 'scheduled'", () => {
    render(<StatusBadge status="scheduled" />);
    expect(screen.getByText(/scheduled/i)).toBeInTheDocument();
  });

  it("renderiza o texto do status 'handoff'", () => {
    render(<StatusBadge status="handoff" />);
    expect(screen.getByText(/handoff/i)).toBeInTheDocument();
  });

  it("renderiza o texto do status 'qualifying'", () => {
    render(<StatusBadge status="qualifying" />);
    expect(screen.getByText(/qualifying/i)).toBeInTheDocument();
  });

  it("nao usa gradiente decorativo", () => {
    const { container } = render(<StatusBadge status="new" />);
    const badge = container.firstElementChild as HTMLElement;
    expect(badge.className).not.toMatch(/gradient/);
  });
});
