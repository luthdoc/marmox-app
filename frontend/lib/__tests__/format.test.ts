import { describe, it, expect } from "vitest";
import { maskPhone, formatDate } from "../format";

describe("maskPhone", () => {
  it("mascara os digitos do meio mantendo os 4 ultimos visíveis", () => {
    const result = maskPhone("+5511987654321");
    expect(result).toMatch(/\+55 11 9\*{4}-4321/);
  });

  it("retorna valor original se telefone tiver menos de 11 digitos", () => {
    const result = maskPhone("12345");
    expect(result).toBe("12345");
  });

  it("funciona com telefone de 11 digitos sem DDI", () => {
    const result = maskPhone("11987654321");
    expect(result).toMatch(/\*{4}-4321|9\*{4}-4321/);
  });
});

describe("formatDate", () => {
  it("formata data ISO com dia, mes, ano, hora e minuto em pt-BR", () => {
    // Usa uma data fixa para evitar dependencia de timezone local
    const result = formatDate("2024-03-15T10:30:00.000Z");
    // O resultado depende do timezone da maquina, mas sempre tem dia/mes/ano e hora:minuto
    expect(result).toMatch(/\d{2}\/\d{2}\/\d{4}/); // DD/MM/AAAA
    expect(result).toMatch(/\d{2}:\d{2}/); // HH:mm
  });

  it("retorna traço para data nula ou vazia", () => {
    expect(formatDate("")).toBe("—");
    expect(formatDate(null as unknown as string)).toBe("—");
  });
});
