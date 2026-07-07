"use client";

import { useCallback, useEffect, useState } from "react";
import { Mail, Plus, Users } from "lucide-react";
import { api, type Participant } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type Props = {
  meetingId: string;
};

type Row = {
  name: string;
  email: string;
  role: string;
  slack_username: string;
};

const emptyRow = (): Row => ({
  name: "",
  email: "",
  role: "",
  slack_username: "",
});

export function MeetingParticipantsCard({ meetingId }: Props) {
  const [participants, setParticipants] = useState<Participant[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [draft, setDraft] = useState<Row>(emptyRow());

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const meeting = await api.meetings.get(meetingId);
      setParticipants(meeting.participants);
    } catch {
      setParticipants([]);
    } finally {
      setLoading(false);
    }
  }, [meetingId]);

  useEffect(() => {
    void load();
  }, [load]);

  const addParticipant = async () => {
    if (!draft.name.trim() || !draft.email.trim()) {
      setMessage("Nome e email são obrigatórios.");
      return;
    }
    setSaving(true);
    setMessage(null);
    try {
      await api.meetings.addParticipant(meetingId, {
        name: draft.name.trim(),
        email: draft.email.trim(),
        role: draft.role.trim() || null,
        slack_username: draft.slack_username.trim() || null,
      });
      setDraft(emptyRow());
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Erro ao adicionar.");
    } finally {
      setSaving(false);
    }
  };

  const handleImport = async () => {
    const raw = prompt(
      "Cole CSV: nome,email,cargo,slack (uma linha por participante)"
    );
    if (!raw) return;
    const rows = raw
      .split("\n")
      .map((line) => {
        const [name, email, role, slack_username] = line
          .split(",")
          .map((s) => s.trim());
        return {
          name: name || "",
          email: email || "",
          role: role || null,
          slack_username: slack_username || null,
        };
      })
      .filter((r) => r.name && r.email);
    if (!rows.length) {
      setMessage("Nenhuma linha válida no CSV.");
      return;
    }
    setSaving(true);
    setMessage(null);
    try {
      await api.meetings.importParticipants(meetingId, rows);
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Erro ao importar.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-2">
        <CardTitle className="flex items-center gap-2 text-base">
          <Users className="h-5 w-5" />
          Participantes (email da ata)
        </CardTitle>
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={saving}
          onClick={() => void handleImport()}
        >
          Importar CSV
        </Button>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-slate-600">
          O email da ata aprovada é enviado para estas pessoas.
        </p>

        {loading ? (
          <p className="text-sm text-slate-500">A carregar…</p>
        ) : participants.length === 0 ? (
          <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
            Ainda não há participantes — adiciona pelo menos um email abaixo.
          </p>
        ) : (
          <ul className="space-y-2">
            {participants.map((p) => (
              <li
                key={p.id}
                className="flex flex-wrap items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm"
              >
                <span className="font-medium text-slate-900">{p.name}</span>
                <span className="flex items-center gap-1 text-slate-600">
                  <Mail className="h-3.5 w-3.5" />
                  {p.email}
                </span>
                {p.role ? (
                  <span className="text-xs text-slate-500">({p.role})</span>
                ) : null}
              </li>
            ))}
          </ul>
        )}

        <div className="grid gap-2 rounded-lg border border-dashed border-slate-300 p-4 sm:grid-cols-2">
          <Input
            placeholder="Nome"
            value={draft.name}
            onChange={(e) => setDraft({ ...draft, name: e.target.value })}
          />
          <Input
            placeholder="Email"
            type="email"
            value={draft.email}
            onChange={(e) => setDraft({ ...draft, email: e.target.value })}
          />
          <Input
            placeholder="Cargo (opcional)"
            value={draft.role}
            onChange={(e) => setDraft({ ...draft, role: e.target.value })}
          />
          <Input
            placeholder="Slack username (opcional)"
            value={draft.slack_username}
            onChange={(e) =>
              setDraft({ ...draft, slack_username: e.target.value })
            }
          />
          <Button
            type="button"
            className="sm:col-span-2"
            disabled={saving}
            onClick={() => void addParticipant()}
          >
            <Plus className="h-4 w-4" />
            Adicionar participante
          </Button>
        </div>

        {message && <p className="text-sm text-red-600">{message}</p>}
      </CardContent>
    </Card>
  );
}
