import { MeetingForm } from "@/components/meetings/meeting-form";

export default function NewMeetingPage() {
  return (
    <div className="p-8">
      <h1 className="mb-2 text-2xl font-bold text-slate-900">Criar Reunião</h1>
      <p className="mb-8 text-slate-500">
        Preencha os dados da reunião e adicione participantes
      </p>
      <MeetingForm />
    </div>
  );
}
