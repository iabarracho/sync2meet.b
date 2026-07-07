"use client";

import { useEffect, useState } from "react";
import { Clock } from "lucide-react";
import { api } from "@/lib/api";

type Props = {
  className?: string;
  compact?: boolean;
};

export function RetentionNotice({ className = "", compact = false }: Props) {
  const [days, setDays] = useState<number | null>(null);

  useEffect(() => {
    api.health()
      .then((h) => setDays(h.meeting_retention_days ?? 15))
      .catch(() => setDays(15));
  }, []);

  if (days === null || days <= 0) return null;

  const detail = compact
    ? "Os templates na página Templates mantêm-se. Envia a ata por email para guardar reuniões."
    : "Só as reuniões são apagadas (gravações, transcrições, atas). Os templates de agenda e ata na página Templates mantêm-se — são da equipa e não expiram.";

  return (
    <div
      className={`flex gap-2 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950 ${className}`}
      role="status"
    >
      <Clock className="mt-0.5 h-4 w-4 shrink-0 text-amber-700" />
      <p>
        <strong>Retenção de {days} dias:</strong> cada reunião é apagada
        automaticamente {days} dias após a criação. {detail}
      </p>
    </div>
  );
}
