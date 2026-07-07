import { notFound } from "next/navigation";
import { api } from "@/lib/api";
import { EmailSentView } from "@/components/meetings/email-sent-view";
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
    return { title: pageTitle(`Email enviado — ${meeting.title}`) };
  } catch {
    return { title: pageTitle("Email enviado") };
  }
}

export default async function EmailSentPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ distribution?: string }>;
}) {
  const { id } = await params;
  const { distribution } = await searchParams;
  let meeting;
  try {
    meeting = await api.meetings.get(id);
  } catch {
    notFound();
  }

  return (
    <div className="p-8">
      <EmailSentView
        meetingId={id}
        meetingTitle={meeting.title}
        distributionId={distribution ?? null}
      />
    </div>
  );
}
