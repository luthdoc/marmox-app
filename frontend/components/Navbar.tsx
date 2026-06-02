"use client";

import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase";
import { Button } from "./ui/Button";

export function Navbar() {
  const router = useRouter();
  const supabase = createClient();

  async function handleSignOut() {
    await supabase.auth.signOut();
    router.push("/login");
  }

  return (
    <nav className="flex items-center justify-between px-4 sm:px-6 py-3 bg-[var(--color-canvas)] border-b border-[var(--color-hairline)]">
      <span className="text-[17px] font-semibold text-[var(--color-ink)]">
        Marmax
      </span>
      <Button variant="utility" onClick={handleSignOut} className="text-sm py-1.5">
        Sair
      </Button>
    </nav>
  );
}
