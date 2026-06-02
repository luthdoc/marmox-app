import { StatusBadge } from "./ui/StatusBadge";
import { maskPhone, formatDate } from "@/lib/format";

type LeadStatus =
  | "new"
  | "qualifying"
  | "qualified"
  | "scheduled"
  | "handoff"
  | "cold";

interface Lead {
  id: string;
  name: string | null;
  phone: string;
  service_type: string;
  status: LeadStatus;
  last_contact_at: string;
}

interface LeadRowProps {
  lead: Lead;
  onClick: (id: string) => void;
}

export function LeadRow({ lead, onClick }: LeadRowProps) {
  const displayName = lead.name || maskPhone(lead.phone);

  return (
    <tr
      role="row"
      onClick={() => onClick(lead.id)}
      className="border-b border-[var(--color-hairline)] hover:bg-[var(--color-canvas-parchment)] cursor-pointer transition-colors"
    >
      <td className="py-3 pr-4 text-[17px] text-[var(--color-ink)]">
        {displayName}
      </td>
      <td className="py-3 pr-4 text-[17px] text-[var(--color-ink-muted)] hidden sm:table-cell">
        {lead.service_type}
      </td>
      <td className="py-3 pr-4">
        <StatusBadge status={lead.status} />
      </td>
      <td className="py-3 text-[15px] text-[var(--color-ink-muted)]">
        {formatDate(lead.last_contact_at)}
      </td>
    </tr>
  );
}
