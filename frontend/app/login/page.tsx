import { LoginForm } from "./LoginForm";

export default function LoginPage() {
  return (
    <main className="min-h-screen flex items-center justify-center bg-[var(--color-canvas-parchment)] px-4">
      <div className="w-full max-w-sm">
        <h1 className="text-[28px] font-semibold text-[var(--color-ink)] mb-8 text-center">
          Marmax
        </h1>
        <LoginForm />
      </div>
    </main>
  );
}
