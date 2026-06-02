import React from "react";

type LeadStatus =
  | "new"
  | "qualifying"
  | "qualified"
  | "scheduled"
  | "handoff"
  | "cold";

interface StatusBadgeProps {
  status: LeadStatus;
}

const statusConfig: Record<LeadStatus, { label: string; className: string }> = {
  new: {
    label: "new",
    className: "bg-[#e8f0fb] text-[var(--color-action-blue)]",
  },
  qualifying: {
    label: "qualifying",
    className: "bg-[#fff3e0] text-[#b45309]",
  },
  qualified: {
    label: "qualified",
    className: "bg-[#e6f4ea] text-[#1a7f37]",
  },
  scheduled: {
    label: "scheduled",
    className: "bg-[#e8f0fb] text-[#1558d6]",
  },
  handoff: {
    label: "handoff",
    className: "bg-[#f3e8ff] text-[#7c3aed]",
  },
  cold: {
    label: "cold",
    className: "bg-[var(--color-canvas-parchment)] text-[var(--color-ink-muted)]",
  },
};

export function StatusBadge({ status }: StatusBadgeProps) {
  const { label, className } = statusConfig[status];
  return (
    <span
      className={`inline-flex items-center rounded-[9999px] px-3 py-0.5 text-sm font-medium ${className}`}
    >
      {label}
    </span>
  );
}
