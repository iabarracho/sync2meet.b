import { TemplatesManager } from "@/components/templates/templates-manager";
import { pageTitle } from "@/lib/branding";

export const metadata = {
  title: pageTitle("Templates"),
};

export default function TemplatesPage() {
  return (
    <div className="p-8">
      <h1 className="mb-2 text-2xl font-bold text-slate-900">Templates</h1>
      <p className="mb-2 text-slate-500">
        Modelos de agenda e ata partilhados pela equipa. Não são apagados com a
        retenção de 15 dias das reuniões.
      </p>
      <p className="mb-8 text-sm text-slate-400">
        Para usar numa reunião, escolhe o template na página da reunião.
      </p>
      <TemplatesManager />
    </div>
  );
}
