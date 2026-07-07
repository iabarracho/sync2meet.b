"use client";

import { useRouter } from "next/navigation";
import { Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";

type Props = {
  meetingId: string;
  title: string;
};

export function MeetingDeleteButton({ meetingId, title }: Props) {
  const router = useRouter();

  const handleDelete = async () => {
    const ok = window.confirm(
      `Apagar a reunião "${title}"?\n\nIsto remove gravações, transcrições e atas associadas.`
    );
    if (!ok) return;
    try {
      await api.meetings.delete(meetingId);
      router.push("/meetings");
      router.refresh();
    } catch (err) {
      window.alert(err instanceof Error ? err.message : "Não foi possível apagar.");
    }
  };

  return (
    <Button
      type="button"
      variant="outline"
      size="sm"
      className="text-red-600 hover:bg-red-50 hover:text-red-700"
      onClick={() => void handleDelete()}
    >
      <Trash2 className="h-4 w-4" />
      Apagar reunião
    </Button>
  );
}
