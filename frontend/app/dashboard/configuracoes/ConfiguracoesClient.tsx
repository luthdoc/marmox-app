"use client";

import { createClient } from "@/lib/supabase";
import { Card } from "@/components/ui/Card";
import { InlineField } from "@/components/InlineField";

interface TenantConfig {
  name: string;
  services: string[];
  regions: string[];
  business_hours: string;
  welcome_message: string;
}

interface ConfiguracoesClientProps {
  tenant: TenantConfig;
}

function parseList(raw: string): string[] {
  return raw
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

export function ConfiguracoesClient({ tenant }: ConfiguracoesClientProps) {
  const supabase = createClient();

  async function saveField(field: keyof TenantConfig, rawValue: string) {
    const value =
      field === "services" || field === "regions"
        ? parseList(rawValue)
        : rawValue;

    const { error } = await supabase
      .from("tenants")
      .update({ [field]: value })
      .eq("id", (await supabase.auth.getUser()).data.user?.id ?? "");

    if (error) {
      throw new Error("Erro ao salvar. Tente novamente.");
    }
  }

  function validateRequired(value: string): string | null {
    return value.trim() ? null : "Campo obrigatório";
  }

  function validateList(value: string): string | null {
    const items = parseList(value);
    return items.length > 0 ? null : "Informe ao menos um item";
  }

  return (
    <div className="max-w-xl flex flex-col gap-6">
      <h1 className="text-[28px] font-semibold text-[var(--color-ink)]">
        Configurações da Empresa
      </h1>

      <Card>
        <div className="flex flex-col gap-6">
          <InlineField
            label="Nome da empresa"
            value={tenant.name}
            onSave={(v) => saveField("name", v)}
            validate={validateRequired}
          />

          <InlineField
            label="Serviços (separados por vírgula)"
            value={tenant.services.join(", ")}
            onSave={(v) => saveField("services", v)}
            validate={validateList}
          />

          <InlineField
            label="Regiões atendidas (separadas por vírgula)"
            value={tenant.regions.join(", ")}
            onSave={(v) => saveField("regions", v)}
            validate={validateList}
          />

          <InlineField
            label="Horários de funcionamento"
            value={tenant.business_hours}
            onSave={(v) => saveField("business_hours", v)}
            validate={validateRequired}
            multiline
          />

          <InlineField
            label="Mensagem de boas-vindas"
            value={tenant.welcome_message}
            onSave={(v) => saveField("welcome_message", v)}
            validate={validateRequired}
            multiline
          />
        </div>
      </Card>
    </div>
  );
}
