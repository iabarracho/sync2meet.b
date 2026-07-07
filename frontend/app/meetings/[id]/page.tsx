import Link from "next/link";
import { notFound } from "next/navigation";
import { Pencil } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/ui/badge";
import { MeetingWorkflow } from "@/components/meetings/meeting-workflow";
import { MeetingDeleteButton } from "@/components/meetings/meeting-delete-button";
import { RetentionNotice } from "@/components/meetings/retention-notice";
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
    return { title: pageTitle(meeting.title) };
  } catch {
    return { title: pageTitle("Reunião") };
  }
}

export default async function MeetingDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  let bundle;
  try {
    bundle = await api.meetings.fetchPageBundle(id);
  } catch {
    notFound();
  }

  const { meeting, recordings, transcript, agenda, minutes, templates } =
    bundle;

  return (
    <div className="p-8">
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">{meeting.title}</h1>
          <p className="text-slate-500">{meeting.client_name}</p>
          {meeting.meeting_date && (
            <p className="mt-1 text-sm text-slate-400">
              {meeting.meeting_date}
              {meeting.meeting_time ? ` · ${meeting.meeting_time}` : ""}
            </p>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <Button variant="outline" size="sm" asChild>
            <Link href={`/meetings/${id}/edit`}>
              <Pencil className="h-4 w-4" />
              Editar emails
            </Link>
          </Button>
          <StatusBadge status={meeting.status} />
          <MeetingDeleteButton meetingId={id} title={meeting.title} />
        </div>
      </div>
      <RetentionNotice className="mb-6" />
      <MeetingWorkflow
        meetingId={id}
        initialStatus={meeting.status}
        initialRecordings={recordings}
        initialTranscript={transcript}
        initialAgenda={agenda}
        initialMinutes={minutes}
        initialTemplates={templates}
      />
    </div>
  );
}
