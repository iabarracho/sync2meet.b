"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Trash2 } from "lucide-react";
import { api, type MeetingListItem } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/badge";

type Props = {
  meetings: MeetingListItem[];
};

export function MeetingsList({ meetings }: Props) {
  const router = useRouter();

  const handleDelete = async (e: React.MouseEvent, meeting: MeetingListItem) => {
    e.preventDefault();
    e.stopPropagation();
    const ok = window.confirm(
      `Apagar a reunião "${meeting.title}"?\n\nIsto remove gravações, transcrições e atas associadas.`
    );
    if (!ok) return;
    try {
      await api.meetings.delete(meeting.id);
      router.refresh();
    } catch (err) {
      window.alert(err instanceof Error ? err.message : "Não foi possível apagar.");
    }
  };

  return (
    <div className="space-y-3">
      {meetings.map((m) => (
        <Link key={m.id} href={`/meetings/${m.id}`}>
          <Card className="transition-shadow hover:shadow-md">
            <CardHeader className="flex flex-row items-center justify-between py-4">
              <div>
                <CardTitle className="text-base">{m.title}</CardTitle>
                <p className="text-sm text-slate-500">{m.client_name}</p>
              </div>
              <div className="flex items-center gap-3">
                {m.meeting_date && (
                  <span className="text-sm text-slate-500">{m.meeting_date}</span>
                )}
                <StatusBadge status={m.status} />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="text-red-600 hover:bg-red-50 hover:text-red-700"
                  onClick={(e) => void handleDelete(e, m)}
                  title="Apagar reunião"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </CardHeader>
          </Card>
        </Link>
      ))}
    </div>
  );
}
