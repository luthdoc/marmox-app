"use client";

import { useRouter } from "next/navigation";
import { LeadRow } from "@/components/LeadRow";

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

interface LeadsClientProps {
  leads: Lead[];
}

export function LeadsClient({ leads }: LeadsClientProps) {
  const router = useRouter();

  if (leads.length === 0) {
    return (
      <div className="flex items-center justify-center py-24">
        <p className="text-[17px] text-[var(--color-ink-muted)]">
          Nenhum lead ainda.
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-[18px] bg-[var(--color-canvas)]">
      <table className="w-full">
        <thead>
          <tr className="border-b border-[var(--color-hairline)]">
            <th className="py-3 pr-4 text-left text-xs font-medium text-[var(--color-ink-muted)] uppercase tracking-wide">
              Nome
            </th>
            <th className="py-3 pr-4 text-left text-xs font-medium text-[var(--color-ink-muted)] uppercase tracking-wide hidden sm:table-cell">
              Serviço
            </th>
            <th className="py-3 pr-4 text-left text-xs font-medium text-[var(--color-ink-muted)] uppercase tracking-wide">
              Status
            </th>
            <th className="py-3 text-left text-xs font-medium text-[var(--color-ink-muted)] uppercase tracking-wide">
              Último contato
            </th>
          </tr>
        </thead>
        <tbody>
          {leads.map((lead) => (
            <LeadRow
              key={lead.id}
              lead={lead}
              onClick={(id) => router.push(`/dashboard/leads/${id}`)}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}
