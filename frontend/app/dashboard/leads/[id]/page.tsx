import Link from "next/link";
import { createSupabaseServerClient } from "@/lib/supabase-server";
import { LeadDetails } from "@/components/LeadDetails";
import { ConversationView } from "@/components/ConversationView";
import { Button } from "@/components/ui/Button";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function LeadDetailPage({ params }: PageProps) {
  const { id } = await params;
  const supabase = await createSupabaseServerClient();

  const { data: lead } = await supabase
    .from("leads")
    .select(
      "id, name, phone, service_type, material, urgency, neighborhood, status, last_contact_at"
    )
    .eq("id", id)
    .single();

  if (!lead) {
    return (
      <div className="flex flex-col items-center justify-center py-24 gap-4">
        <p className="text-[17px] text-[var(--color-ink)]">Lead não encontrado.</p>
        <Link href="/dashboard/leads" className="text-[var(--color-action-blue)] hover:underline">
          Voltar para a lista
        </Link>
      </div>
    );
  }

  // Busca conversa associada ao lead
  const { data: conversation } = await supabase
    .from("conversations")
    .select("id")
    .eq("lead_id", id)
    .maybeSingle();

  let messages: {
    id: string;
    content: string;
    direction: "inbound" | "outbound";
    created_at: string;
    media_url: string | null;
  }[] = [];

  if (conversation) {
    const { data: msgs } = await supabase
      .from("messages")
      .select("id, content, direction, created_at, media_url")
      .eq("conversation_id", conversation.id)
      .order("created_at", { ascending: true });

    messages = (msgs ?? []) as typeof messages;
  }

  return (
    <div className="max-w-2xl flex flex-col gap-6">
      <div className="flex items-center gap-4">
        <Link href="/dashboard/leads">
          <Button variant="utility" className="text-sm py-1.5">
            Voltar
          </Button>
        </Link>
        <h1 className="text-[28px] font-semibold text-[var(--color-ink)]">
          {lead.name ?? "Lead"}
        </h1>
      </div>

      <LeadDetails lead={lead} />

      <section>
        <h2 className="text-[21px] font-semibold text-[var(--color-ink)] mb-4">
          Conversa
        </h2>
        <div className="rounded-[18px] bg-[var(--color-canvas)] p-4">
          <ConversationView messages={messages} />
        </div>
      </section>
    </div>
  );
}
