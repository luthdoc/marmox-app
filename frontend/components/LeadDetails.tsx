import { StatusBadge } from "./ui/StatusBadge";
import { Card } from "./ui/Card";
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
  material: string | null;
  urgency: string | null;
  neighborhood: string | null;
  status: LeadStatus;
  last_contact_at: string;
}

interface LeadDetailsProps {
  lead: Lead;
}

interface FieldProps {
  label: string;
  value: string | null | undefined;
}

function Field({ label, value }: FieldProps) {
  if (!value) return null;
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-xs font-medium text-[var(--color-ink-muted)] uppercase tracking-wide">
        {label}
      </span>
      <span className="text-[17px] text-[var(--color-ink)]">{value}</span>
    </div>
  );
}

export function LeadDetails({ lead }: LeadDetailsProps) {
  return (
    <Card>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Field label="Nome" value={lead.name} />
        <Field label="Telefone" value={maskPhone(lead.phone)} />
        <Field label="Serviço" value={lead.service_type} />
        <Field label="Material" value={lead.material} />
        <Field label="Urgência" value={lead.urgency} />
        <Field label="Bairro" value={lead.neighborhood} />
        <Field label="Último contato" value={formatDate(lead.last_contact_at)} />
        <div className="flex flex-col gap-0.5">
          <span className="text-xs font-medium text-[var(--color-ink-muted)] uppercase tracking-wide">
            Status
          </span>
          <StatusBadge status={lead.status} />
        </div>
      </div>
    </Card>
  );
}
