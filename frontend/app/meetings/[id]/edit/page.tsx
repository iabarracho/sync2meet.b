import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { MeetingParticipantsCard } from "@/components/meetings/meeting-participants-card";
import { pageTitle } from "@/lib/branding";

export const dynamic = "force-dynamic";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  try {
    const meeting = await api.meetings.get(id);
    return { title: pageTitle(`Editar — ${meeting.title}`) };
  } catch {
    return { title: pageTitle("Editar participantes") };
  }
}

export default async function MeetingEditPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  let meeting;
  try {
    meeting = await api.meetings.get(id);
  } catch {
    notFound();
  }

  return (
    <div className="p-8">
      <div className="mb-6">
        <Button variant="outline" size="sm" asChild>
          <Link href={`/meetings/${id}`}>
            <ArrowLeft className="h-4 w-4" />
            Voltar à reunião
          </Link>
        </Button>
      </div>
      <h1 className="mb-1 text-2xl font-bold text-slate-900">Editar participantes</h1>
      <p className="mb-8 text-slate-500">
        {meeting.title} — emails para envio da ata
      </p>
      <div className="max-w-2xl">
        <MeetingParticipantsCard meetingId={id} />
      </div>
    </div>
  );
}
