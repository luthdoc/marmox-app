import { createSupabaseServerClient } from "@/lib/supabase-server";
import { ConfiguracoesClient } from "./ConfiguracoesClient";

export default async function ConfiguracoesPage() {
  const supabase = await createSupabaseServerClient();

  const {
    data: { user },
  } = await supabase.auth.getUser();

  const { data: tenant } = await supabase
    .from("tenants")
    .select("name, services, regions, business_hours, welcome_message")
    .eq("user_id", user?.id ?? "")
    .single();

  const safeTenant = {
    name: tenant?.name ?? "",
    services: tenant?.services ?? [],
    regions: tenant?.regions ?? [],
    business_hours: tenant?.business_hours ?? "",
    welcome_message: tenant?.welcome_message ?? "",
  };

  return <ConfiguracoesClient tenant={safeTenant} />;
}
