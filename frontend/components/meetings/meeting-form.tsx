"use client";



import { useState } from "react";

import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";

import { Input } from "@/components/ui/input";

import { Label } from "@/components/ui/label";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

import { api } from "@/lib/api";



type ParticipantRow = {

  name: string;

  email: string;

  role: string;

  slack_username: string;

};



export function MeetingForm() {

  const router = useRouter();

  const [loading, setLoading] = useState(false);

  const [error, setError] = useState<string | null>(null);

  const [clientName, setClientName] = useState("");

  const [title, setTitle] = useState("");

  const [meetingDate, setMeetingDate] = useState("");

  const [meetingTime, setMeetingTime] = useState("");

  const [description, setDescription] = useState("");

  const [participants, setParticipants] = useState<ParticipantRow[]>([

    { name: "", email: "", role: "", slack_username: "" },

  ]);



  const addRow = () =>

    setParticipants([

      ...participants,

      { name: "", email: "", role: "", slack_username: "" },

    ]);



  const updateRow = (i: number, field: keyof ParticipantRow, value: string) => {

    const next = [...participants];

    next[i] = { ...next[i], [field]: value };

    setParticipants(next);

  };



  const handleImport = () => {

    const raw = prompt(

      "Cole CSV: nome,email,cargo,slack (uma linha por participante)"

    );

    if (!raw) return;

    const rows = raw.split("\n").map((line) => {

      const [name, email, role, slack_username] = line.split(",").map((s) => s.trim());

      return { name: name || "", email: email || "", role: role || "", slack_username: slack_username || "" };

    });

    setParticipants(rows.filter((r) => r.name && r.email));

  };



  const submit = async (e: React.FormEvent) => {

    e.preventDefault();

    setLoading(true);

    setError(null);

    try {

      const meeting = await api.meetings.create({

        client_name: clientName,

        title,

        meeting_date: meetingDate || null,

        meeting_time: meetingTime || null,

        description: description || null,

        participants: participants

          .filter((p) => p.name && p.email)

          .map((p) => ({

            name: p.name,

            email: p.email,

            role: p.role || null,

            slack_username: p.slack_username || null,

          })),

      });

      router.push(`/meetings/${meeting.id}`);

    } catch (err) {

      setError(err instanceof Error ? err.message : "Erro ao criar reunião");

    } finally {

      setLoading(false);

    }

  };



  return (

    <form onSubmit={submit} className="max-w-2xl space-y-6">

      <Card>

        <CardHeader>

          <CardTitle>Dados da reunião</CardTitle>

        </CardHeader>

        <CardContent className="space-y-4">

          <div>

            <Label htmlFor="client">Nome do cliente</Label>

            <Input

              id="client"

              required

              value={clientName}

              onChange={(e) => setClientName(e.target.value)}

            />

          </div>

          <div>

            <Label htmlFor="title">Título</Label>

            <Input

              id="title"

              required

              value={title}

              onChange={(e) => setTitle(e.target.value)}

            />

          </div>

          <div className="grid grid-cols-2 gap-4">

            <div>

              <Label htmlFor="date">Data</Label>

              <Input

                id="date"

                type="date"

                value={meetingDate}

                onChange={(e) => setMeetingDate(e.target.value)}

              />

            </div>

            <div>

              <Label htmlFor="time">Hora</Label>

              <Input

                id="time"

                type="time"

                value={meetingTime}

                onChange={(e) => setMeetingTime(e.target.value)}

              />

            </div>

          </div>

          <div>

            <Label htmlFor="desc">Descrição (opcional)</Label>

            <Input

              id="desc"

              value={description}

              onChange={(e) => setDescription(e.target.value)}

            />

          </div>

        </CardContent>

      </Card>



      <Card>

        <CardHeader className="flex flex-row items-center justify-between">

          <CardTitle>Participantes</CardTitle>

          <div className="flex gap-2">

            <Button type="button" variant="outline" size="sm" onClick={handleImport}>

              Importar

            </Button>

            <Button type="button" variant="outline" size="sm" onClick={addRow}>

              Adicionar

            </Button>

          </div>

        </CardHeader>

        <CardContent className="space-y-4">

          {participants.map((p, i) => (

            <div key={i} className="grid gap-2 rounded-lg border p-4 sm:grid-cols-2">

              <Input

                placeholder="Nome"

                value={p.name}

                onChange={(e) => updateRow(i, "name", e.target.value)}

              />

              <Input

                placeholder="Email"

                type="email"

                value={p.email}

                onChange={(e) => updateRow(i, "email", e.target.value)}

              />

              <Input

                placeholder="Cargo (opcional)"

                value={p.role}

                onChange={(e) => updateRow(i, "role", e.target.value)}

              />

              <Input

                placeholder="Slack username"

                value={p.slack_username}

                onChange={(e) => updateRow(i, "slack_username", e.target.value)}

              />

            </div>

          ))}

        </CardContent>

      </Card>



      {error && <p className="text-sm text-red-600">{error}</p>}

      <Button type="submit" disabled={loading}>

        {loading ? "A guardar…" : "Criar Reunião"}

      </Button>

    </form>

  );

}


