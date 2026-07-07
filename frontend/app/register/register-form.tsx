"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { safeNextPath } from "@/lib/auth";
import { APP_NAME } from "@/lib/branding";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function RegisterForm() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [allowed, setAllowed] = useState<boolean | null>(null);
  const [emailDomains, setEmailDomains] = useState<string[]>([]);

  useEffect(() => {
    api.auth
      .config()
      .then((cfg) => {
        setAllowed(cfg.allow_registration);
        setEmailDomains(cfg.allowed_email_domains ?? []);
      })
      .catch(() => setAllowed(false));
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
      ? `Apenas emails ${emailDomains.map((d) => `@${d}`).join(", ")}.`
      : null;

  if (allowed === null) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 p-6">
        <p className="text-slate-500">A carregar…</p>
      </div>
    );
  }

  if (!allowed) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 p-6">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle>Registo fechado</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-slate-600">
              O limite de contas foi atingido ou o registo está desativado.
              Pede a um administrador para te ajudar.
            </p>
            <Button asChild variant="outline" className="w-full">
              <Link href="/login">Voltar ao login</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 p-6">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Criar conta — {APP_NAME}</CardTitle>
          <p className="text-sm text-slate-500">
            Cada pessoa cria a sua própria conta com email e password.
            {domainHint ? ` ${domainHint}` : ""}
          </p>
        </CardHeader>
        <CardContent>
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
            <p className="text-center text-sm text-slate-500">
              Já tens conta?{" "}
              <Link href="/login" className="text-brand-600 hover:underline">
                Entrar
              </Link>
            </p>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
