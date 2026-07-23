"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Check,
  FileDown,
  FileText,
  FileVideo,
  Mail,
  MessageSquare,
  Mic,
  Pencil,
  Play,
  Sparkles,
  Trash2,
  Upload,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  api,
  formatBytes,
  parseApiError,
  transcriptText,
  waitForJob,
  type Agenda,
  type MeetingStatus,
  type Recording,
  type Summary,
  type Template,
  type Transcript,
} from "@/lib/api";
import {
  pickDefaultTemplateId,
  TemplateSelect,
} from "@/components/meetings/template-select";
import { GoogleMeetImport } from "@/components/meetings/google-meet-import";
import { saveEmailSentResult } from "@/lib/email-sent";

/** Alinhado com backend MAX_UPLOAD_BYTES (2 GB). */
const MAX_UPLOAD_BYTES = 2 * 1024 * 1024 * 1024;

function splitTemplates(all: Template[]) {
  return {
    agenda: all.filter((t) => t.type === "agenda"),
    minutes: all.filter((t) => t.type === "minutes"),
  };
}

type Props = {
  meetingId: string;
  initialStatus: MeetingStatus;
  initialRecordings?: Recording[];
  initialTranscript?: Transcript | null;
  initialAgenda?: Agenda | null;
  initialMinutes?: Summary | null;
  initialTemplates?: Template[];
};

export function MeetingWorkflow({
  meetingId,
  initialStatus,
  initialRecordings,
  initialTranscript,
  initialAgenda,
  initialMinutes,
  initialTemplates,
}: Props) {
  const initialTemplateSplit = splitTemplates(initialTemplates ?? []);
  const ssrHydrated =
    initialRecordings !== undefined ||
    initialTranscript !== undefined ||
    initialTemplates !== undefined;
  const router = useRouter();
  const [status, setStatus] = useState(initialStatus);
  const [agendaContent, setAgendaContent] = useState(initialAgenda?.content ?? "");
  const [minutesContent, setMinutesContent] = useState(
    initialMinutes?.content ?? ""
  );
  const [minutesApproved, setMinutesApproved] = useState(
    initialMinutes?.is_approved ?? false
  );
  const [summaryId, setSummaryId] = useState<string | null>(
    initialMinutes?.id ?? null
  );
  const [slackPreview, setSlackPreview] = useState<string | null>(null);
  const [slackEnabled, setSlackEnabled] = useState(false);
  const [slackChannel, setSlackChannel] = useState("#general");
  const [loading, setLoading] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const [agendaTemplates, setAgendaTemplates] = useState<Template[]>(
    initialTemplateSplit.agenda
  );
  const [minutesTemplates, setMinutesTemplates] = useState<Template[]>(
    initialTemplateSplit.minutes
  );
  const [selectedAgendaTemplateId, setSelectedAgendaTemplateId] = useState(() =>
    pickDefaultTemplateId(initialTemplateSplit.agenda)
  );
  const [selectedMinutesTemplateId, setSelectedMinutesTemplateId] = useState(() =>
    pickDefaultTemplateId(initialTemplateSplit.minutes)
  );
  const [docType, setDocType] = useState<"agenda" | "minutes">("minutes");
  const [templatesLoading, setTemplatesLoading] = useState(
    initialTemplates === undefined
  );
  const [recordings, setRecordings] = useState<Recording[]>(
    initialRecordings ?? []
  );
  const [transcript, setTranscript] = useState<Transcript | null>(
    initialTranscript ?? null
  );
  const [mediaLoading, setMediaLoading] = useState(
    initialRecordings === undefined && initialTranscript === undefined
  );
  const agendaDirtyRef = useRef(false);
  const minutesDirtyRef = useRef(false);

  const applyWorkflow = useCallback(
    (data: Awaited<ReturnType<typeof api.meetings.fetchWorkflow>>) => {
      setRecordings(data.recordings);
      setTranscript(data.transcript);
      if (data.agenda) setAgendaContent(data.agenda.content);
      if (data.minutes) {
        setMinutesContent(data.minutes.content);
        setSummaryId(data.minutes.id);
        setMinutesApproved(data.minutes.is_approved);
      }
    },
    []
  );

  const loadWorkflow = useCallback(async () => {
    setMediaLoading(true);
    try {
      const data = await api.meetings.fetchWorkflow(meetingId);
      applyWorkflow(data);
    } catch {
      /* mantém dados SSR / estado anterior */
    } finally {
      setMediaLoading(false);
    }
  }, [applyWorkflow, meetingId]);

  useEffect(() => {
    if (!ssrHydrated) void loadWorkflow();
  }, [loadWorkflow, ssrHydrated]);

  const applyTemplates = useCallback((all: Template[]) => {
    const { agenda, minutes } = splitTemplates(all);
    setAgendaTemplates(agenda);
    setMinutesTemplates(minutes);
    setSelectedAgendaTemplateId((prev) =>
      agenda.some((t) => t.id === prev) ? prev : pickDefaultTemplateId(agenda)
    );
    setSelectedMinutesTemplateId((prev) =>
      minutes.some((t) => t.id === prev)
        ? prev
        : pickDefaultTemplateId(minutes)
    );
  }, []);

  const loadTemplates = useCallback(async () => {
    setTemplatesLoading(true);
    try {
      applyTemplates(await api.templates.list());
    } catch {
      setAgendaTemplates([]);
      setMinutesTemplates([]);
      setSelectedAgendaTemplateId("");
      setSelectedMinutesTemplateId("");
    } finally {
      setTemplatesLoading(false);
    }
  }, [applyTemplates]);

  useEffect(() => {
    if (initialTemplates === undefined) void loadTemplates();
  }, [initialTemplates, loadTemplates]);

  useEffect(() => {
    api.auth
      .config()
      .then((cfg) => {
        setSlackEnabled(Boolean(cfg.slack_enabled));
        if (cfg.slack_default_channel) {
          setSlackChannel(cfg.slack_default_channel);
        }
      })
      .catch(() => setSlackEnabled(false));
  }, []);

  useEffect(() => {
    setStatus(initialStatus);
    if (initialRecordings !== undefined) setRecordings(initialRecordings);
    if (initialTranscript !== undefined) setTranscript(initialTranscript);
    if (initialAgenda !== undefined && !agendaDirtyRef.current) {
      setAgendaContent(initialAgenda?.content ?? "");
    }
    if (initialMinutes !== undefined && !minutesDirtyRef.current) {
      setMinutesContent(initialMinutes?.content ?? "");
      setSummaryId(initialMinutes?.id ?? null);
      setMinutesApproved(initialMinutes?.is_approved ?? false);
    }
    if (initialTemplates !== undefined) {
      applyTemplates(initialTemplates);
      setTemplatesLoading(false);
    }
  }, [
    applyTemplates,
    initialAgenda,
    initialMinutes,
    initialRecordings,
    initialStatus,
    initialTemplates,
    initialTranscript,
  ]);

  const run = useCallback(
    async (key: string, fn: () => Promise<void>) => {
      setLoading(key);
      setMessage(null);
      try {
        await fn();
        router.refresh();
      } catch (err) {
        const raw = err instanceof Error ? err.message : "Erro";
        setMessage(parseApiError(raw));
      } finally {
        setLoading(null);
      }
    },
    [router]
  );

  const loadAgenda = async () => {
    const a = await api.meetings.getAgenda(meetingId);
    if (a) {
      agendaDirtyRef.current = false;
      setAgendaContent(a.content);
    }
  };

  const loadMinutes = async () => {
    const m = await api.meetings.getMinutes(meetingId);
    if (m) {
      minutesDirtyRef.current = false;
      setMinutesContent(m.content);
      setSummaryId(m.id);
      setMinutesApproved(m.is_approved);
    }
  };

  const templatesHint = (
    <>
      Sem templates. Reinicia com{" "}
      <strong>ARRANCAR.cmd</strong> ou vê a página{" "}
      <Link href="/templates" className="font-medium text-brand-600 hover:underline">
        Templates
      </Link>
      .
    </>
  );

  const saveMinutesDraft = useCallback(async () => {
    if (!summaryId || minutesApproved) return;
    await api.meetings.updateMinutes(meetingId, minutesContent);
  }, [meetingId, minutesContent, minutesApproved, summaryId]);

  const transcriptBody = transcriptText(transcript);
  const hasTranscript = Boolean(transcriptBody);
  const hasMinutes = Boolean(summaryId || minutesContent.trim());
  const hasAgenda = Boolean(agendaContent.trim());
  const activeTemplates =
    docType === "agenda" ? agendaTemplates : minutesTemplates;
  const selectedTemplateId =
    docType === "agenda" ? selectedAgendaTemplateId : selectedMinutesTemplateId;
  const setSelectedTemplateId =
    docType === "agenda"
      ? setSelectedAgendaTemplateId
      : setSelectedMinutesTemplateId;

  return (
    <div className="space-y-6">
      <p className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
        <strong>Como funciona:</strong> primeiro carregas o áudio ou transcrição.
        Depois escolhes <em>agenda</em> ou <em>ata</em> e geras a partir do que
        foi dito — nada é criado sem gravação.
        <span className="mt-1 block text-xs text-slate-500">
          Transcrição: OpenAI Whisper (rápido) ou Whisper local se configurado.
          Se aparecer «Amara.org» ou texto repetido, o áudio não tem fala clara —
          usa a gravação da reunião ou VTT do Google Meet.
        </span>
      </p>

      {message && (
        <p
          role="alert"
          className="rounded-lg bg-red-50 px-4 py-2 text-sm text-red-700"
        >
          {message}
        </p>
      )}
      {successMessage && (
        <p
          role="status"
          aria-live="polite"
          className="rounded-lg bg-green-50 px-4 py-2 text-sm text-green-800"
        >
          {successMessage}
        </p>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Play className="h-5 w-5" />
            1. Gravação & Transcrição
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <GoogleMeetImport
            meetingId={meetingId}
            disabled={!!loading}
            onSuccess={(msg) => {
              setSuccessMessage(msg);
              setMessage(null);
              setStatus("recorded");
              void loadWorkflow();
              router.refresh();
            }}
            onError={(msg) => {
              setMessage(msg);
              setSuccessMessage(null);
            }}
          />

          {!mediaLoading && (recordings.length > 0 || transcript) && (
            <div className="rounded-lg border border-green-200 bg-green-50 p-4 text-sm text-green-900">
              <p className="mb-2 font-semibold">Ficheiros carregados</p>
              <ul className="space-y-2">
                {recordings.map((rec) => (
                  <li key={rec.id} className="flex flex-wrap items-center gap-2">
                    <FileVideo className="h-4 w-4 shrink-0 text-green-700" />
                    <span className="font-medium">{rec.filename}</span>
                    {rec.size_bytes ? (
                      <span className="text-green-700">({formatBytes(rec.size_bytes)})</span>
                    ) : null}
                    <span className="rounded bg-white px-1.5 py-0.5 text-xs text-green-800 ring-1 ring-green-200">
                      {rec.source === "google_meet_transcript"
                        ? "transcrição"
                        : rec.source === "google_meet"
                          ? "gravação Meet"
                          : "gravação"}
                    </span>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="ml-auto h-7 text-red-600 hover:bg-red-50"
                      disabled={!!loading}
                      onClick={() =>
                        run("delete-recording", async () => {
                          const ok = window.confirm(
                            `Apagar "${rec.filename}"?\n\nA transcrição ligada também será removida.`
                          );
                          if (!ok) return;
                          await api.meetings.deleteRecording(meetingId, rec.id);
                          setSuccessMessage("Gravação apagada.");
                          const updated = await api.meetings.get(meetingId);
                          setStatus(updated.status);
                          await loadWorkflow();
                          router.refresh();
                        })
                      }
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                      Apagar
                    </Button>
                  </li>
                ))}
              </ul>
              {transcript && (
                <div className="mt-3 border-t border-green-200 pt-3">
                  <div className="mb-1 flex items-center justify-between gap-2">
                    <p className="text-xs font-medium text-green-800">
                      Transcrição disponível ({transcript.provider})
                    </p>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="h-7 text-red-600 hover:bg-red-50"
                      disabled={!!loading}
                      onClick={() =>
                        run("delete-transcript", async () => {
                          const ok = window.confirm(
                            "Apagar a transcrição?\n\nPodes voltar a transcrever ou carregar outro ficheiro."
                          );
                          if (!ok) return;
                          await api.meetings.deleteTranscript(meetingId);
                          setSuccessMessage("Transcrição apagada.");
                          const updated = await api.meetings.get(meetingId);
                          setStatus(updated.status);
                          await loadWorkflow();
                          router.refresh();
                        })
                      }
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                      Apagar transcrição
                    </Button>
                  </div>
                  <p className="line-clamp-3 font-mono text-xs text-green-900/90">
                    {transcriptBody.slice(0, 400)}
                    {transcriptBody.length > 400 ? "…" : ""}
                  </p>
                </div>
              )}
            </div>
          )}

          <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            disabled={!!loading}
            onClick={() =>
              run("start", async () => {
                await api.meetings.start(meetingId);
                setStatus("in_progress");
              })
            }
          >
            Iniciar Reunião
          </Button>
          <label className="inline-flex cursor-pointer">
            <input
              type="file"
              className="hidden"
              accept=".webm,.mp4,.mp3,.wav,.m4a,.ogg,audio/*,video/*"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (!file) return;
                if (file.size > MAX_UPLOAD_BYTES) {
                  setMessage(
                    "Ficheiro demasiado grande (máximo 2 GB). Comprime o áudio ou divide a gravação."
                  );
                  e.target.value = "";
                  return;
                }
                run("upload", async () => {
                  const rec = await api.meetings.uploadRecording(meetingId, file);
                  setStatus("recorded");
                  setSuccessMessage(
                    `Gravação carregada: ${rec.filename}${
                      rec.size_bytes ? ` (${formatBytes(rec.size_bytes)})` : ""
                    }`
                  );
                  await loadWorkflow();
                });
              }}
            />
            <Button variant="outline" asChild>
              <span>
                <Upload className="h-4 w-4" />
                Carregar Gravação
              </span>
            </Button>
          </label>
          <Button
            disabled={!!loading}
            onClick={() =>
              run("transcribe", async () => {
                setStatus("processing");
                const job = await api.meetings.transcribe(meetingId);
                const done = await waitForJob(
                  meetingId,
                  job.id,
                  api.meetings.getJob
                );
                if (done.status === "failed") {
                  throw new Error(done.error || "Transcrição falhou");
                }
                setStatus("recorded");
                setSuccessMessage(
                  "Transcrição concluída. Escolhe o tipo de documento no passo 2."
                );
                await loadWorkflow();
                document
                  .getElementById("meeting-step-2")
                  ?.scrollIntoView({ behavior: "smooth", block: "start" });
              })
            }
          >
            <Mic className="h-4 w-4" />
            {loading === "transcribe" ? "A transcrever…" : "Transcrever (áudio)"}
          </Button>
          </div>
        </CardContent>
      </Card>

      <Card
        id="meeting-step-2"
        className={hasTranscript ? "ring-2 ring-brand-500/30" : undefined}
      >
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5" />
            2. Escolher tipo e gerar
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {hasTranscript && !mediaLoading && (
            <p className="rounded-lg border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-900">
              Transcrição pronta — escolhe o template e clica em{" "}
              <strong>Gerar Ata</strong> ou <strong>Gerar Agenda</strong>.
            </p>
          )}

          {!hasTranscript && !mediaLoading && (
            <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
              Carrega e transcreve a reunião no passo 1 antes de gerar qualquer
              documento.
            </p>
          )}

          <div>
            <p className="mb-2 text-sm font-medium text-slate-700">
              Que tipo de documento queres?
            </p>
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                variant={docType === "minutes" ? "default" : "outline"}
                disabled={!!loading}
                onClick={() => setDocType("minutes")}
              >
                Ata da reunião
              </Button>
              <Button
                type="button"
                variant={docType === "agenda" ? "default" : "outline"}
                disabled={!!loading}
                onClick={() => setDocType("agenda")}
              >
                Agenda
              </Button>
            </div>
          </div>

          <TemplateSelect
            stepHint={
              docType === "minutes"
                ? "Escolhe o template da ata"
                : "Escolhe o template da agenda"
            }
            label={docType === "minutes" ? "Template da ata" : "Template da agenda"}
            templates={activeTemplates}
            value={selectedTemplateId}
            onChange={setSelectedTemplateId}
            disabled={templatesLoading || !!loading || !hasTranscript}
            loading={templatesLoading}
            emptyHint={templatesHint}
          />
          <div className="flex justify-end">
            <Button
              variant="ghost"
              size="sm"
              disabled={templatesLoading || !!loading}
              onClick={() =>
                run("refresh-templates", async () => {
                  await loadTemplates();
                  setSuccessMessage("Lista de templates atualizada.");
                })
              }
            >
              Atualizar templates
            </Button>
          </div>

          <div className="flex flex-wrap gap-2">
            <Button
              disabled={
                !!loading ||
                templatesLoading ||
                !hasTranscript ||
                !selectedTemplateId
              }
              onClick={() =>
                run("generate", async () => {
                  if (!selectedTemplateId) return;
                  if (docType === "agenda") {
                    const job = await api.meetings.generateAgenda(
                      meetingId,
                      selectedTemplateId
                    );
                    const done = await waitForJob(
                      meetingId,
                      job.id,
                      api.meetings.getJob
                    );
                    if (done.status === "failed") {
                      throw new Error(done.error || "Geração da agenda falhou");
                    }
                    await loadAgenda();
                    setDocType("agenda");
                    setStatus("agenda_ready");
                    setSuccessMessage("Agenda gerada a partir da transcrição.");
                  } else {
                    const job = await api.meetings.generateMinutes(
                      meetingId,
                      selectedTemplateId
                    );
                    const done = await waitForJob(
                      meetingId,
                      job.id,
                      api.meetings.getJob
                    );
                    if (done.status === "failed") {
                      throw new Error(done.error || "Geração da ata falhou");
                    }
                    await loadMinutes();
                    setDocType("minutes");
                    setStatus("pending_approval");
                    setSuccessMessage(
                      "Ata gerada. Revisa o texto no passo 3."
                    );
                  }
                  document
                    .getElementById("meeting-generated-document")
                    ?.scrollIntoView({ behavior: "smooth", block: "start" });
                })
              }
            >
              <Sparkles className="h-4 w-4" />
              {loading === "generate"
                ? "A gerar…"
                : docType === "minutes"
                  ? "Gerar Ata"
                  : "Gerar Agenda"}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card id="meeting-generated-document">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            3. Documento gerado
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {(hasAgenda || hasMinutes) && (
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                size="sm"
                variant={docType === "minutes" ? "default" : "outline"}
                disabled={!hasMinutes}
                onClick={() => setDocType("minutes")}
              >
                Ata
                {!hasMinutes ? " (vazio)" : ""}
              </Button>
              <Button
                type="button"
                size="sm"
                variant={docType === "agenda" ? "default" : "outline"}
                disabled={!hasAgenda}
                onClick={() => setDocType("agenda")}
              >
                Agenda
                {!hasAgenda ? " (vazio)" : ""}
              </Button>
            </div>
          )}
          {docType === "agenda" ? (
            <>
              <p className="text-sm text-slate-500">
                Edita o texto se precisares. Usa <strong>Pré-visualizar Word</strong>{" "}
                para ver o documento final.
              </p>
              <div className="flex flex-wrap gap-2">
                <Button
                  variant="outline"
                  disabled={!agendaContent || !!loading}
                  onClick={() =>
                    run("preview-agenda-word", async () => {
                      const filename = await api.meetings.exportAgendaDocx(
                        meetingId,
                        agendaContent
                      );
                      setSuccessMessage(
                        `Descarregado: ${filename}. Abre na pasta Transferências.`
                      );
                    })
                  }
                >
                  <FileDown className="h-4 w-4" />
                  Pré-visualizar Word
                </Button>
              </div>
              <textarea
                className="min-h-[280px] w-full rounded-lg border border-slate-200 p-3 font-mono text-sm"
                value={agendaContent}
                onChange={(e) => {
                  agendaDirtyRef.current = true;
                  setAgendaContent(e.target.value);
                }}
                placeholder="A agenda gerada aparece aqui…"
              />
            </>
          ) : (
            <>
              <p className="text-sm text-slate-500">
                Edita a ata aqui. Antes de aprovar, usa{" "}
                <strong>Pré-visualizar Word</strong> para ver o documento como
                fica no Word.
              </p>
              <div className="flex flex-wrap gap-2">
                <Button
                  variant="outline"
                  disabled={!minutesContent || !!loading}
                  onClick={() =>
                    run("preview-word", async () => {
                      const filename = await api.meetings.exportMinutesDocx(
                        meetingId,
                        minutesContent
                      );
                      setSuccessMessage(
                        `Descarregado: ${filename}. Abre na pasta Transferências e revê no Word antes de aprovar.`
                      );
                    })
                  }
                >
                  <FileDown className="h-4 w-4" />
                  {loading === "preview-word"
                    ? "A gerar Word…"
                    : "Pré-visualizar Word"}
                </Button>
              </div>
              <textarea
                className="min-h-[280px] w-full rounded-lg border border-slate-200 p-3 font-mono text-sm disabled:bg-slate-50 disabled:text-slate-600"
                value={minutesContent}
                onChange={(e) => {
                  minutesDirtyRef.current = true;
                  setMinutesContent(e.target.value);
                }}
                readOnly={minutesApproved}
                placeholder="A ata gerada aparece aqui — edita antes de aprovar…"
              />
              {minutesApproved && (
                <p className="text-xs text-slate-500">
                  Ata aprovada — para alterar, gera uma nova versão no passo 2.
                </p>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {hasMinutes && (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Check className="h-5 w-5" />
            4. Aprovação & Distribuição
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-slate-500">
            Revê a ata no passo 3. Podes aprovar só a versão ou enviar diretamente
            por email — ao enviar, a ata é aprovada automaticamente.
          </p>
          <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            disabled={!summaryId || !minutesContent || minutesApproved || !!loading}
            onClick={() =>
              run("approve", async () => {
                if (!summaryId) return;
                await saveMinutesDraft();
                await api.meetings.approve(meetingId, summaryId);
                setStatus("approved");
                setMinutesApproved(true);
                setSuccessMessage("Ata aprovada.");
              })
            }
          >
            Aprovar Ata
          </Button>
          <Button
            variant="outline"
            asChild
          >
            <Link href={`/meetings/${meetingId}/edit`}>
              <Pencil className="h-4 w-4" />
              Editar emails
            </Link>
          </Button>
          <Button
            disabled={!summaryId || !minutesContent || !!loading}
            onClick={() =>
              run("email", async () => {
                if (!summaryId) return;
                await saveMinutesDraft();
                const idempotencyKey = crypto.randomUUID();
                const dist = await api.meetings.distributeEmail(
                  meetingId,
                  idempotencyKey
                );
                const sentTo = dist.logs
                  .filter((log) => log.status === "sent")
                  .map((log) => log.to_email);
                setStatus("distributed");
                setMinutesApproved(true);
                saveEmailSentResult(meetingId, {
                  distributionId: dist.id,
                  emails: sentTo,
                  sentAt: new Date().toISOString(),
                });
                router.push(
                  `/meetings/${meetingId}/email-sent?distribution=${dist.id}`
                );
              })
            }
          >
            <Mail className="h-4 w-4" />
            Enviar por Email
          </Button>
          <Button
            variant="outline"
            disabled={!!loading || !slackEnabled}
            title={
              slackEnabled
                ? undefined
                : "Slack não configurado no servidor (SLACK_BOT_TOKEN)."
            }
            onClick={() =>
              run("slack-preview", async () => {
                const p = await api.meetings.slackPreview(meetingId);
                setSlackPreview(p.message);
                setSuccessMessage(
                  `Pré-visualização Slack pronta (canal ${p.channel}).`
                );
              })
            }
          >
            <MessageSquare className="h-4 w-4" />
            Pré-visualizar Slack
          </Button>
          <Button
            variant="outline"
            disabled={!!loading || !slackEnabled}
            title={
              slackEnabled
                ? undefined
                : "Slack não configurado no servidor (SLACK_BOT_TOKEN)."
            }
            onClick={() =>
              run("slack-send", async () => {
                const log = await api.meetings.slackSend(meetingId);
                const channel =
                  log &&
                  typeof log === "object" &&
                  "channel" in log &&
                  typeof (log as { channel?: string }).channel === "string"
                    ? (log as { channel: string }).channel
                    : slackChannel;
                setSuccessMessage(`Enviado para o Slack (${channel}).`);
              })
            }
          >
            Enviar para Slack
          </Button>
          </div>
          {!slackEnabled ? (
            <p className="text-xs text-amber-700">
              Slack desactivado: falta <code>SLACK_BOT_TOKEN</code> no servidor
              (e o bot tem de estar no canal {slackChannel}).
            </p>
          ) : (
            <p className="text-xs text-slate-500">
              Slack envia para {slackChannel}. O bot tem de estar convidado
              nesse canal.
            </p>
          )}
        </CardContent>
        {slackPreview && (
          <CardContent className="pt-0">
            <pre className="whitespace-pre-wrap rounded-lg bg-slate-900 p-4 text-sm text-slate-100">
              {slackPreview}
            </pre>
          </CardContent>
        )}
      </Card>
      )}

      <p className="text-xs text-slate-400">
        Estado atual: <strong>{status}</strong>
      </p>
    </div>
  );
}
