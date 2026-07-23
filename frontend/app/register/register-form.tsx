"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { safeNextPath } from "@/lib/auth";
import { AuthShell } from "@/components/auth/auth-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function RegisterForm() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [allowed, setAllowed] = useState<boolean | null>(null);
  const [configError, setConfigError] = useState<string | null>(null);
  const [emailDomains, setEmailDomains] = useState<string[]>([]);

  useEffect(() => {
    api.auth
      .config()
      .then((cfg) => {
        setAllowed(cfg.allow_registration);
        setEmailDomains(cfg.allowed_email_domains ?? []);
        setConfigError(null);
      })
      .catch(() => {
        setAllowed(false);
        setConfigError(
          "Não foi possível contactar a API. Verifica se o servidor Sync2meet está a correr."
        );
      });
  }, []);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (password !== confirm) {
      setError("As passwords não coincidem.");
      return;
    }

    setLoading(true);
    try {
      await api.auth.register(name.trim(), email.trim(), password);
      router.push(safeNextPath("/"));
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha no registo");
    } finally {
      setLoading(false);
    }
  }

  const domainHint =
    emailDomains.length > 0
      ? ` Apenas emails ${emailDomains.map((d) => `@${d}`).join(", ")}.`
      : "";

  if (allowed === null) {
    return (
      <AuthShell title="Criar conta" subtitle="A carregar…">
        <p className="text-sm text-neutral-500">A carregar…</p>
      </AuthShell>
    );
  }

  if (!allowed) {
    return (
      <AuthShell
        title="Registo fechado"
        subtitle={
          configError ??
          "O limite de contas foi atingido ou o registo está desativado. Pede a um administrador para te ajudar."
        }
      >
        <Button asChild variant="outline" className="w-full">
          <Link href="/login">Voltar ao login</Link>
        </Button>
      </AuthShell>
    );
  }

  return (
    <AuthShell
      title="Criar conta"
      subtitle={`Cada pessoa cria a sua própria conta com email e password.${domainHint}`}
    >
      <form onSubmit={onSubmit} className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="name">Nome</Label>
          <Input
            id="name"
            autoComplete="name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="password">Password (mín. 8 caracteres)</Label>
          <Input
            id="password"
            type="password"
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            minLength={8}
            required
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="confirm">Confirmar password</Label>
          <Input
            id="confirm"
            type="password"
            autoComplete="new-password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            minLength={8}
            required
          />
        </div>
        {error ? <p className="text-sm text-red-600">{error}</p> : null}
        <Button type="submit" className="w-full" disabled={loading}>
          {loading ? "A criar conta…" : "Criar conta"}
        </Button>
        <p className="text-center text-sm text-neutral-500">
          Já tens conta?{" "}
          <Link
            href="/login"
            className="font-medium text-neutral-900 underline-offset-2 hover:underline"
          >
            Entrar
          </Link>
        </p>
      </form>
    </AuthShell>
  );
}
