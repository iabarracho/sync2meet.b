"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { ChevronDown, FileText, Sparkles } from "lucide-react";
import { Label } from "@/components/ui/label";
import type { Template } from "@/lib/api";

type Props = {
  label: string;
  stepHint: string;
  templates: Template[];
  value: string;
  onChange: (templateId: string) => void;
  disabled?: boolean;
  loading?: boolean;
  emptyHint?: ReactNode;
};

function templateBadge(t: Template) {
  return t.is_default ? "Padrão" : "Template";
}

export function TemplateSelect({
  label,
  stepHint,
  templates,
  value,
  onChange,
  disabled,
  loading,
  emptyHint,
}: Props) {
  const selected = templates.find((t) => t.id === value);

  if (loading) {
    return (
      <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-500">
        A carregar templates…
      </div>
    );
  }

  if (templates.length === 0) {
    return (
      <div className="rounded-xl border-2 border-dashed border-amber-300 bg-amber-50 px-4 py-4 text-sm text-amber-950">
        <p className="mb-1 font-semibold">① Escolhe um template — indisponível</p>
        <p>
          {emptyHint ||
            "Nenhum template disponível. Abre Templates com o backend ligado."}
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border-2 border-brand-200 bg-brand-50/40 p-4">
      <div className="mb-3 flex items-start gap-3">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-brand-600 text-white">
          <FileText className="h-4 w-4" />
        </div>
        <div>
          <p className="text-sm font-semibold text-brand-900">{stepHint}</p>
          <p className="text-xs text-brand-800/80">
            Nada é criado sozinho — escolhe um template na lista e só depois
            clica em <Sparkles className="inline h-3 w-3" /> Gerar.
          </p>
        </div>
      </div>

      <div className="space-y-2">
        <Label className="text-slate-700">{label}</Label>
        <div className="relative">
          <select
            className="h-11 w-full appearance-none rounded-lg border border-brand-300 bg-white py-2 pl-3 pr-10 text-sm font-medium text-slate-900 shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 disabled:opacity-50"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            disabled={disabled}
            aria-label={label}
          >
            <option value="">— Escolhe um template —</option>
            {templates.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
                {t.is_default ? " (predefinido)" : " (teu)"}
              </option>
            ))}
          </select>
          <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        </div>
        {selected ? (
          <p className="text-xs text-slate-600">
            Seleccionado: <strong>{selected.name}</strong>
            {" · "}
            <span className="rounded bg-white px-1.5 py-0.5 text-brand-700 ring-1 ring-brand-200">
              {templateBadge(selected)}
            </span>
          </p>
        ) : (
          <p className="text-xs text-amber-800">
            Escolhe um predefinido na lista ou adiciona o teu em Templates.
          </p>
        )}
        <p className="text-xs text-slate-500">
          <Link href="/templates" className="font-medium text-brand-600 hover:underline">
            + Adicionar o meu template
          </Link>
        </p>
      </div>
    </div>
  );
}

export function pickDefaultTemplateId(templates: Template[]): string {
  const def = templates.find((t) => t.is_default);
  return def?.id ?? templates[0]?.id ?? "";
}
