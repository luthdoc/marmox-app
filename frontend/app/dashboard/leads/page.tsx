import { createSupabaseServerClient } from "@/lib/supabase-server";
import { LeadsClient } from "./LeadsClient";

export default async function LeadsPage() {
  const supabase = await createSupabaseServerClient();

  const { data: leads } = await supabase
    .from("leads")
    .select("id, name, phone, service_type, status, last_contact_at")
    .order("last_contact_at", { ascending: false });

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-[28px] font-semibold text-[var(--color-ink)]">Leads</h1>
      <LeadsClient leads={leads ?? []} />
    </div>
  );
}
