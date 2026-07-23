"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

export function ApiStatusBanner() {
  const [status, setStatus] = useState<"ok" | "offline" | "wrong" | null>(null);

  useEffect(() => {
    fetch("/api/health")
      .then(async (r) => {
        if (!r.ok) throw new Error("offline");
        const data = (await r.json()) as { status?: string; message?: string };
        if (data.status === "ok") {
          setStatus("ok");
          return;
        }
        setStatus("wrong");
      })
      .catch(() => setStatus("offline"));
  }, []);

  if (status !== "offline" && status !== "wrong") return null;

  return (
    <div className="border-b border-amber-300 bg-amber-50 px-6 py-3 text-sm text-amber-950">
      {status === "wrong" ? (
        <>
          <strong>Backend errado na porta 8000.</strong> Outra aplicação está a
          usar essa porta. Corre{" "}
          <code className="rounded bg-amber-100 px-1">parar-tudo.cmd</code> e
          depois <code className="rounded bg-amber-100 px-1">ARRANCAR.cmd</code>.
        </>
      ) : (
        <>
          <strong>API offline (porta 8000).</strong> Templates, reuniões e login
          não funcionam até arrancares o backend.{" "}
          <span className="text-amber-800">
            Duplo-clique em{" "}
            <code className="rounded bg-amber-100 px-1">ARRANCAR.cmd</code> na
            pasta do projeto. Docker <strong>não</strong> é necessário.
          </span>{" "}
          <Link href="/templates" className="underline">
            Templates
          </Link>
        </>
      )}
    </div>
  );
}
