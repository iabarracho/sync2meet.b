"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { APP_NAME } from "@/lib/branding";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function ForgotPasswordForm() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [available, setAvailable] = useState<boolean | null>(null);

  useEffect(() => {
    api.auth
      .config()
      .then((cfg) => setAvailable(cfg.password_reset_enabled ?? false))
      .catch(() => setAvailable(false));
  }, []);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    setLoading(true);
    try {
      const result = await api.auth.forgotPassword(email.trim());
      setSuccess(result.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha no pedido");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 p-6">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>{APP_NAME}</CardTitle>
          <p className="text-sm text-slate-500">
            Recuperar password — enviamos um link para o teu email.
          </p>
        </CardHeader>
        <CardContent>
          {available === false ? (
            <p className="text-sm text-amber-700">
              A recuperação por email ainda não está configurada no servidor.
              Contacta o administrador.
            </p>
          ) : (
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
              {error ? <p className="text-sm text-red-600">{error}</p> : null}
              {success ? (
                <p className="text-sm text-green-700">{success}</p>
              ) : null}
              <Button
                type="submit"
                className="w-full"
                disabled={loading || available === null}
              >
                {loading ? "A enviar…" : "Enviar link"}
              </Button>
            </form>
          )}
          <p className="mt-4 text-center text-sm text-slate-500">
            <Link href="/login" className="text-brand-600 hover:underline">
              Voltar ao login
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
