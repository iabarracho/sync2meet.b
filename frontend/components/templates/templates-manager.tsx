"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AlertCircle, RefreshCw, RotateCcw, Star, Trash2, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, type Template } from "@/lib/api";

function canDeleteTemplate(t: Template): boolean {
  return t.can_delete !== false;
}

export function TemplatesManager() {
  const router = useRouter();
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(true);
  const [apiError, setApiError] = useState<string | null>(null);
  const [uploadName, setUploadName] = useState("");
  const [uploadType, setUploadType] = useState<"agenda" | "minutes">("agenda");
  const [busy, setBusy] = useState(false);

  const copyCount = templates.filter(
    (t) =>
      t.can_delete !== false &&
      (t.name.toLowerCase().includes("cópia") ||
        t.name.toLowerCase().includes("copia"))
  ).length;
  const duplicateCount =
    templates.length -
    new Set(templates.map((t) => `${t.name}::${t.type}`)).size;
  const extrasCount = Math.max(copyCount, duplicateCount);

  const loadTemplates = useCallback(async () => {
    setLoading(true);
    setApiError(null);
    try {
      const list = await api.templates.list();
      setTemplates(list);
      if (list.length === 0) {
        setApiError(
          "Nenhum template encontrado. Reinicia com ARRANCAR.cmd — são criados automaticamente."
        );
      }
    } catch (err) {
      let msg =
        err instanceof Error ? err.message : "Não foi possível ligar à API";
      if (
        msg.includes("ECONNREFUSED") ||
        msg.includes("Failed to fetch") ||
        msg.includes("fetch failed")
      ) {
        msg =
          "Backend offline (porta 8000). Corre ARRANCAR.cmd na pasta do projeto.";
      }
      setApiError(msg);
      setTemplates([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTemplates();
  }, [loadTemplates]);

  const refresh = async () => {
    await loadTemplates();
    router.refresh();
  };

  const cleanupCopies = async () => {
    setBusy(true);
    try {
      const result = await api.templates.cleanupCopies();
      await refresh();
      if (result.removed === 0) {
        setApiError(null);
      }
    } catch (err) {
      setApiError(err instanceof Error ? err.message : "Erro ao limpar cópias");
    } finally {
      setBusy(false);
    }
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !uploadName) return;
    setBusy(true);
    try {
      await api.templates.upload(uploadName, uploadType, file);
      await refresh();
      setUploadName("");
    } catch (err) {
      setApiError(err instanceof Error ? err.message : "Erro no upload");
    } finally {
      setBusy(false);
    }
  };

  const apiOffline = templates.length === 0 && !!apiError;

  return (
    <div className="space-y-8">
      {apiError && (
        <div className="flex gap-3 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" />
          <div className="space-y-2">
            <p className="font-medium">Atenção</p>
            <p>{apiError}</p>
            <Button
              size="sm"
              variant="outline"
              onClick={loadTemplates}
              disabled={loading}
            >
              <RefreshCw className="h-4 w-4" />
              Tentar novamente
            </Button>
          </div>
        </div>
      )}

      {!apiOffline && extrasCount > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950">
          <p>
            Tens templates duplicados. Clica abaixo para ficares só com um de
            cada.
          </p>
          <Button
            size="sm"
            variant="outline"
            onClick={cleanupCopies}
            disabled={busy}
          >
            <Trash2 className="h-4 w-4" />
            Remover cópias
          </Button>
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Carregar template personalizado</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-4">
          <div>
            <Label>Nome</Label>
            <Input
              value={uploadName}
              onChange={(e) => setUploadName(e.target.value)}
              disabled={apiOffline}
            />
          </div>
          <div>
            <Label>Tipo</Label>
            <select
              className="h-10 rounded-lg border border-slate-200 px-3 text-sm"
              value={uploadType}
              onChange={(e) =>
                setUploadType(e.target.value as "agenda" | "minutes")
              }
              disabled={apiOffline}
            >
              <option value="agenda">Agenda</option>
              <option value="minutes">Ata</option>
            </select>
          </div>
          <label className="inline-flex cursor-pointer">
            <input
              type="file"
              className="hidden"
              accept=".docx,.pdf,.md,.markdown"
              onChange={handleUpload}
              disabled={busy || !uploadName || apiOffline}
            />
            <span
              className={`inline-flex h-10 items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 text-sm font-medium hover:bg-slate-50 ${
                busy || !uploadName || apiOffline
                  ? "pointer-events-none opacity-50"
                  : ""
              }`}
            >
              <Upload className="h-4 w-4" />
              Carregar ficheiro
            </span>
          </label>
        </CardContent>
      </Card>

      {loading ? (
        <p className="text-sm text-slate-500">A carregar…</p>
      ) : templates.length === 0 ? null : (
        <div className="grid gap-4 md:grid-cols-2">
          {templates.map((t) => (
            <Card key={t.id}>
              <CardHeader className="flex flex-row items-center justify-between gap-2">
                <div className="min-w-0">
                  <CardTitle className="text-base">{t.name}</CardTitle>
                  <p className="text-xs text-slate-500">
                    {t.type === "agenda" ? "Agenda" : "Ata"}
                    {t.is_default ? " · padrão" : ""}
                  </p>
                </div>
                <div className="flex shrink-0 gap-1">
                  {t.source === "docx" && (
                    <Button
                      size="sm"
                      variant="ghost"
                      title="Reimportar texto do Word"
                      onClick={async () => {
                        setBusy(true);
                        try {
                          await api.templates.refreshContent(t.id);
                          await refresh();
                        } catch (err) {
                          setApiError(
                            err instanceof Error
                              ? err.message
                              : "Erro ao reimportar template"
                          );
                        } finally {
                          setBusy(false);
                        }
                      }}
                    >
                      <RotateCcw className="h-4 w-4" />
                    </Button>
                  )}
                  <Button
                    size="sm"
                    variant="ghost"
                    title="Usar por defeito"
                    onClick={async () => {
                      await api.templates.setDefault(t.id);
                      await refresh();
                    }}
                  >
                    <Star
                      className={`h-4 w-4 ${t.is_default ? "fill-amber-400 text-amber-500" : ""}`}
                    />
                  </Button>
                  {canDeleteTemplate(t) && (
                    <Button
                      size="sm"
                      variant="ghost"
                      title="Apagar"
                      className="text-red-600 hover:bg-red-50 hover:text-red-700"
                      onClick={async () => {
                        if (
                          !confirm(
                            `Apagar o template «${t.name}»? Esta acção não pode ser desfeita.`
                          )
                        ) {
                          return;
                        }
                        await api.templates.delete(t.id);
                        await refresh();
                      }}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  )}
                </div>
              </CardHeader>
              <CardContent>
                <pre className="max-h-40 overflow-auto rounded bg-slate-50 p-3 text-xs text-slate-600">
                  {t.content.slice(0, 400)}
                  {t.content.length > 400 ? "…" : ""}
                </pre>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
