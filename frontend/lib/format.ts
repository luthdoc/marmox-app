/**
 * Mascara os dígitos do meio de um número de telefone, mantendo os 4 últimos visíveis.
 * Entrada esperada: +5511987654321 ou 11987654321 (11 dígitos sem DDI)
 * Saída: +55 11 9****-4321
 */
export function maskPhone(phone: string): string {
  const digits = phone.replace(/\D/g, "");

  // Precisa de pelo menos 11 dígitos para aplicar máscara
  if (digits.length < 11) {
    return phone;
  }

  if (digits.length === 13 && digits.startsWith("55")) {
    // +55 DD 9XXXX-XXXX
    const ddd = digits.slice(2, 4);
    const prefix = digits.slice(4, 5);
    const last4 = digits.slice(-4);
    return `+55 ${ddd} ${prefix}****-${last4}`;
  }

  // 11 dígitos: DD 9XXXX-XXXX
  const last4 = digits.slice(-4);
  const prefix = digits.slice(2, 3);
  const ddd = digits.slice(0, 2);
  return `${ddd} ${prefix}****-${last4}`;
}

/**
 * Formata uma data ISO como "DD/MM/AAAA HH:mm" em pt-BR.
 * Retorna "—" para valores nulos ou vazios.
 */
export function formatDate(iso: string): string {
  if (!iso) {
    return "—";
  }

  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(iso));
}
