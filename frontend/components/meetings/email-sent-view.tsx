"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, CheckCircle2, Mail } from "lucide-react";
import { api } from "@/lib/api";
import { emailsFromLogs, readEmailSentResult } from "@/lib/email-sent";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type Props = {
  meetingId: string;
  meetingTitle: string;
  distributionId?: string | null;
};

export function EmailSentView({
  meetingId,
  meetingTitle,
  distributionId,
}: Props) {
  const [emails, setEmails] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      const stored = readEmailSentResult(meetingId, distributionId);
      if (stored?.emails.length) {
        if (!cancelled) {
          setEmails(stored.emails);
          setLoading(false);
        }
        return;
      }

      try {
        if (distributionId) {
          const dist = await api.meetings.getEmailDistribution(
            meetingId,
            distributionId
          );
          if (!cancelled) {
            setEmails(emailsFromLogs(dist.logs));
          }
        } else {
          const logs = await api.meetings.getEmailLogs(meetingId);
          if (!cancelled) {
            setEmails(emailsFromLogs(logs));
          }
        }
      } catch {
        if (!cancelled) setEmails([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [meetingId, distributionId]);

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div className="rounded-2xl border border-green-200 bg-green-50 p-8 text-center">
        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-green-100">
          <CheckCircle2 className="h-9 w-9 text-green-600" />
        </div>
        <h1 className="text-2xl font-bold text-green-900">
          Concluído com sucesso
        </h1>
        <p className="mt-2 text-green-800">
          A ata foi enviada por email aos participantes.
        </p>
        <p className="mt-1 text-sm text-green-700">{meetingTitle}</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Mail className="h-5 w-5" />
            Emails enviados
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-sm text-slate-500">A carregar destinatários…</p>
          ) : emails.length ? (
            <ul className="space-y-2">
              {emails.map((email) => (
                <li
                  key={email}
                  className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-medium text-slate-800"
                >
                  {email}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-slate-500">
              Não foi possível obter a lista de destinatários.
            </p>
          )}
        </CardContent>
      </Card>

      <div className="flex flex-wrap gap-3">
        <Button asChild>
          <Link href={`/meetings/${meetingId}`}>
            <ArrowLeft className="h-4 w-4" />
            Voltar à reunião
          </Link>
        </Button>
        <Button variant="outline" asChild>
          <Link href={`/meetings/${meetingId}/edit`}>Editar emails</Link>
        </Button>
      </div>
    </div>
  );
}
