"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase";
import { Button } from "@/components/ui/Button";

interface FormErrors {
  email?: string;
  password?: string;
}

function validateEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

export function LoginForm() {
  const router = useRouter();
  const supabase = createClient();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<FormErrors>({});
  const [authError, setAuthError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function validate(): boolean {
    const newErrors: FormErrors = {};

    if (!validateEmail(email)) {
      newErrors.email = "Email inválido. Informe um email no formato nome@dominio.com";
    }

    if (!password) {
      newErrors.password = "Senha obrigatória";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setAuthError(null);

    if (!validate()) {
      return;
    }

    setLoading(true);

    const { error } = await supabase.auth.signInWithPassword({ email, password });

    setLoading(false);

    if (error) {
      setAuthError("E-mail ou senha incorretos. Verifique suas credenciais e tente novamente.");
      return;
    }

    router.push("/dashboard");
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4 w-full max-w-sm">
      {authError && (
        <div
          role="alert"
          className="rounded-[8px] border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
        >
          {authError}
        </div>
      )}

      <div className="flex flex-col gap-1">
        <label htmlFor="email" className="text-sm font-medium text-[var(--color-ink)]">
          Email
        </label>
        <input
          id="email"
          type="text"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="rounded-[8px] border border-[var(--color-hairline)] px-4 py-2.5 text-[17px] outline-none focus:border-[var(--color-action-blue)] w-full"
          placeholder="nome@empresa.com"
          autoComplete="email"
        />
        {errors.email && (
          <span className="text-xs text-red-600">{errors.email}</span>
        )}
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="senha" className="text-sm font-medium text-[var(--color-ink)]">
          Senha
        </label>
        <input
          id="senha"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="rounded-[8px] border border-[var(--color-hairline)] px-4 py-2.5 text-[17px] outline-none focus:border-[var(--color-action-blue)] w-full"
          placeholder="Sua senha"
          autoComplete="current-password"
        />
        {errors.password && (
          <span className="text-xs text-red-600">{errors.password}</span>
        )}
      </div>

      <Button
        variant="primary"
        type="submit"
        disabled={loading}
        className="w-full py-3 text-base"
      >
        {loading ? "Entrando..." : "Entrar"}
      </Button>
    </form>
  );
}
