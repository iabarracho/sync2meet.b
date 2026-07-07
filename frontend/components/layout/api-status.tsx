"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

export function ApiStatusBanner() {
  const [ok, setOk] = useState<boolean | null>(null);

  useEffect(() => {
    fetch("/api/health")
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then(() => setOk(true))
      .catch(() => setOk(false));
  }, []);

  if (ok !== false) return null;

  return (
    <div className="border-b border-amber-300 bg-amber-50 px-6 py-3 text-sm text-amber-950">
      <strong>API offline (porta 8000).</strong> Templates, reuniões e Google Meet
      não funcionam até arrancares o backend.{" "}
      <span className="text-amber-800">
        Duplo-clique em{" "}
        <code className="rounded bg-amber-100 px-1">2-BACKEND.cmd</code> na pasta
        do projeto (ou <code className="rounded bg-amber-100 px-1">ARRANCAR.cmd</code>
        ). Docker <strong>não</strong> é necessário.
      </span>{" "}
      <Link href="/templates" className="underline">
        Templates
      </Link>
    </div>
  );
}
