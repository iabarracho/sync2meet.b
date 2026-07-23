"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { clearToken, safeNextPath } from "@/lib/auth";
import { AuthShell } from "@/components/auth/auth-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [emailDomains, setEmailDomains] = useState<string[]>([]);
  const [passwordResetEnabled, setPasswordResetEnabled] = useState(false);

  useEffect(() => {
    api.auth
      .config()
      .then((cfg) => {
        setEmailDomains(cfg.allowed_email_domains ?? []);
        setPasswordResetEnabled(cfg.password_reset_enabled ?? false);
      })
      .catch(() => {
        setEmailDomains([]);
        setPasswordResetEnabled(false);
      });
  }, []);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      clearToken();
      await api.auth.login(email.trim(), password);
      const next = safeNextPath(searchParams.get("next"));
      router.push(next);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha no login");
    } finally {
      setLoading(false);
    }
  }

  const domainHint =
    emailDomains.length > 0
      ? ` Apenas emails ${emailDomains.map((d) => `@${d}`).join(", ")}.`
      : "";

  return (
    <AuthShell
      title="Iniciar sessão"
      subtitle={`Acede às tuas reuniões, agendas e atas.${domainHint}`}
    >
      <form onSubmit={onSubmit} className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            type="email"
            autoComplete="username"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>
        <div className="space-y-2">
          <div className="flex items-center justify-between gap-3">
            <Label htmlFor="password">Password</Label>
            {passwordResetEnabled ? (
              <Link
                href="/forgot-password"
                className="text-xs font-medium text-neutral-700 underline-offset-2 hover:underline"
              >
                Esqueci-me da password
              </Link>
            ) : null}
          </div>
          <Input
            id="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>
        {error ? <p className="text-sm text-red-600">{error}</p> : null}
        <Button type="submit" className="w-full" disabled={loading}>
          {loading ? "A entrar…" : "Entrar"}
        </Button>
        <p className="text-center text-sm text-neutral-500">
          Primeira vez?{" "}
          <Link
            href="/register"
            className="font-medium text-neutral-900 underline-offset-2 hover:underline"
          >
            Criar conta
          </Link>
        </p>
      </form>
    </AuthShell>
  );
}
