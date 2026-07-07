import Link from "next/link";
import { redirect } from "next/navigation";
import {
  Calendar,
  CheckCircle2,
  Clock,
  Mail,
  MessageSquare,
  ListTodo,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { api, ApiError } from "@/lib/api";
import { pageTitle, APP_NAME } from "@/lib/branding";

export const metadata = {
  title: pageTitle("Dashboard"),
};

export const dynamic = "force-dynamic";

export default async function DashboardPage() {
  let stats;
  try {
    stats = await api.dashboard();
  } catch (err) {
    if (err instanceof ApiError && err.status === 401) {
      redirect("/login");
    }
    stats = {
      total_meetings: 0,
      meetings_this_week: 0,
      pending_approval: 0,
      completed_meetings: 0,
      pending_action_items: 0,
      emails_sent: 0,
      slack_messages_sent: 0,
    };
  }

  const cards = [
    {
      label: "Total de reuniões",
      value: stats.total_meetings,
      icon: Calendar,
      color: "text-brand-600",
    },
    {
      label: "Esta semana",
      value: stats.meetings_this_week,
      icon: Clock,
      color: "text-amber-600",
    },
    {
      label: "Pendentes de aprovação",
      value: stats.pending_approval,
      icon: ListTodo,
      color: "text-orange-600",
    },
    {
      label: "Concluídas",
      value: stats.completed_meetings,
      icon: CheckCircle2,
      color: "text-green-600",
    },
    {
      label: "Action items pendentes",
      value: stats.pending_action_items,
      icon: ListTodo,
      color: "text-purple-600",
    },
    {
      label: "Emails enviados",
      value: stats.emails_sent,
      icon: Mail,
      color: "text-blue-600",
    },
    {
      label: "Mensagens Slack",
      value: stats.slack_messages_sent,
      icon: MessageSquare,
      color: "text-pink-600",
    },
  ];

  return (
    <div className="p-8">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
          <p className="text-slate-500">
            Visão geral do ciclo de vida das suas reuniões
          </p>
        </div>
        <Button asChild>
          <Link href="/meetings/new">Criar Reunião</Link>
        </Button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {cards.map(({ label, value, icon: Icon, color }) => (
          <Card key={label}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-slate-500">
                {label}
              </CardTitle>
              <Icon className={`h-4 w-4 ${color}`} />
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-bold">{value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card className="mt-8">
        <CardHeader>
          <CardTitle>Fluxo {APP_NAME}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-slate-600">
            Agenda → Reunião → Transcrição → Ata → Aprovação → Distribuição →
            Follow-up
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
