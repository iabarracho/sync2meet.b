import Link from "next/link";
import { redirect } from "next/navigation";
import { Plus } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { MeetingsList } from "@/components/meetings/meetings-list";
import { RetentionNotice } from "@/components/meetings/retention-notice";
import { pageTitle } from "@/lib/branding";

export const metadata = {
  title: pageTitle("Reuniões"),
};

export const dynamic = "force-dynamic";

export default async function MeetingsPage() {
  let meetings: Awaited<ReturnType<typeof api.meetings.list>> = [];
  try {
    meetings = await api.meetings.list();
  } catch (err) {
    if (err instanceof ApiError && err.status === 401) {
      redirect("/login");
    }
    meetings = [];
  }

  return (
    <div className="p-8">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Reuniões</h1>
          <p className="text-slate-500">Gerir todas as reuniões com clientes</p>
        </div>
        <Button asChild>
          <Link href="/meetings/new">
            <Plus className="h-4 w-4" />
            Criar Reunião
          </Link>
        </Button>
      </div>

      <RetentionNotice className="mb-6" />

      {meetings.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-slate-500">
            Ainda não há reuniões.{" "}
            <Link href="/meetings/new" className="text-brand-600 hover:underline">
              Criar a primeira
            </Link>
          </CardContent>
        </Card>
      ) : (
        <MeetingsList meetings={meetings} />
      )}
    </div>
  );
}
