"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ApiError, api } from "@/lib/api";
import { AuthShell } from "@/components/auth/auth-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function ForgotPasswordForm() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [missingAccount, setMissingAccount] = useState(false);
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
    setMissingAccount(false);
    setLoading(true);
    try {
      const result = await api.auth.forgotPassword(email.trim());
      setSuccess(result.message);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Falha no pedido";
      const isMissing =
        (err instanceof ApiError && err.status === 400) ||
        message.toLowerCase().includes("não existe") ||
        message.toLowerCase().includes("nao existe");
      setMissingAccount(isMissing);
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthShell
      title="Esqueci-me da password"
      subtitle="Escreve o email com que te registaste. Se a conta existir, enviamos o link para esse email."
    >
      {available === false ? (
        <p className="text-sm text-amber-800">
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
          {error ? (
            <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              <p>{error}</p>
              {missingAccount ? (
                <p className="mt-2">
                  <Link
                    href="/register"
                    className="font-medium underline underline-offset-2"
                  >
                    Criar conta nova
                  </Link>
                </p>
              ) : null}
            </div>
          ) : null}
          {success ? (
            <p className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
              {success}
            </p>
          ) : null}
          <Button
            type="submit"
            className="w-full"
            disabled={loading || available === null}
          >
            {loading ? "A verificar…" : "Enviar link"}
          </Button>
        </form>
      )}
      <p className="mt-5 text-center text-sm text-neutral-500">
        <Link
          href="/login"
          className="font-medium text-neutral-900 underline-offset-2 hover:underline"
        >
          Voltar ao login
        </Link>
      </p>
    </AuthShell>
  );
}
