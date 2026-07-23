/** JSON requests use same-origin /api (Next rewrite) or public URL in production. */

import { clearSessionToken } from "@/lib/auth";

function apiBase(): string {
  const configured = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");
  if (configured) return configured;
  if (typeof window !== "undefined") {
    return "";
  }
  return (process.env.INTERNAL_API_URL || "http://127.0.0.1:8000").replace(
    /\/$/,
    ""
  );
}

/** Uploads via route handlers Next.js (cookie HttpOnly → backend). */
function uploadPath(path: string): string {
  return path;
}

async function multipartUpload(path: string, form: FormData): Promise<Response> {
  return fetch(uploadPath(path), {
    method: "POST",
    credentials: "include",
    body: form,
  });
}

async function authHeaders(): Promise<Record<string, string>> {
  if (typeof window !== "undefined") {
    return {};
  }
  const { cookies } = await import("next/headers");
  const token = (await cookies()).get("sync2meet_token")?.value;
  if (!token) return {};
  return { Cookie: `sync2meet_token=${token}` };
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function safeDownloadFilename(raw: string, fallback: string): string {
  const base = raw.split(/[/\\]/).pop()?.replace(/[^\w.\-]+/g, "_") ?? "";
  if (!base || base.length > 200) return fallback;
  return base;
}

async function downloadPostFile(
  path: string,
  fallbackFilename: string,
  body?: Record<string, unknown>
): Promise<string> {
  const auth = await authHeaders();
  const res = await fetch(`${apiBase()}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...auth },
    credentials: "include",
    body: JSON.stringify(body ?? {}),
  });
  if (!res.ok) {
    const err = await res.text();
    if (res.status === 404 && err.includes("Not Found")) {
      throw new Error(
        "Backend desatualizado (falta exportar Word). Fecha a janela «Sync2meet Backend», corre parar-tudo.cmd e ARRANCAR.cmd."
      );
    }
    throw new Error(parseApiError(err));
  }
  const blob = await res.blob();
  if (!blob.size) {
    throw new Error("O ficheiro Word veio vazio. Tenta outra vez.");
  }
  const disposition = res.headers.get("Content-Disposition") ?? "";
  const match = disposition.match(/filename="?([^";\n]+)"?/i);
  const filename = safeDownloadFilename(match?.[1] ?? "", fallbackFilename);
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.rel = "noopener";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
  return filename;
}

function formatBytes(bytes: number | null | undefined): string {
  if (!bytes) return "";
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function parseApiError(raw: string): string {
  const text = raw.trim();
  if (!text) return "Erro desconhecido";
  try {
    const data = JSON.parse(text) as { detail?: string | { msg?: string }[] };
    if (typeof data.detail === "string") return data.detail;
    if (Array.isArray(data.detail) && data.detail[0]?.msg) {
      return data.detail[0].msg;
    }
  } catch {
    /* not JSON */
  }
  if (text.includes("Internal Server Error")) {
    return "Erro no servidor ao carregar ficheiro. Ficheiros grandes (1h+) podem demorar — tenta MP3/M4A comprimido ou reinicia backend e frontend.";
  }
  if (text.includes("Ficheiro demasiado grande")) {
    return text;
  }
  if (text.includes("insufficient_quota") || text.includes("exceeded your current quota")) {
    return "A chave OpenAI não tem saldo/quota. Verifica Billing em platform.openai.com.";
  }
  if (text.includes("Transcreve a reunião primeiro")) {
    return "Falta transcrição. Carrega uma gravação e transcreve, ou importa um ficheiro VTT/TXT.";
  }
  if (
    text.includes("Approve minutes before distribution") ||
    text.includes("Aprova a ata antes de enviar")
  ) {
    return "Aprova a ata antes de enviar o email — clica em «Aprovar Ata» no passo 4.";
  }
  if (text.includes("Editable minutes not found")) {
    return "Esta versão da ata já está aprovada. Gera uma nova ata no passo 2 para editar.";
  }
  if (
    text.includes("BadCredentials") ||
    text.includes("App Password") ||
    text.includes("rejeitou a password SMTP")
  ) {
    return text;
  }
  if (text.includes("Não há destinatários")) {
    return text;
  }
  if (text.includes("Sessão expirada") || text.includes("Inicia sessão")) {
    return "Sessão expirada. Faz logout e volta a entrar, depois tenta outra vez.";
  }
  if (text.length > 280) {
    return "Ocorreu um erro. Tenta novamente ou contacta o administrador.";
  }
  return text;
}

async function request<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const auth = await authHeaders();
  const res = await fetch(`${apiBase()}${path}`, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...auth,
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const err = await res.text();
    throw new ApiError(parseApiError(err || res.statusText), res.status);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export type MeetingStatus =
  | "draft"
  | "agenda_ready"
  | "in_progress"
  | "recorded"
  | "processing"
  | "minutes_ready"
  | "pending_approval"
  | "approved"
  | "distributed";

export interface Participant {
  id: string;
  meeting_id: string;
  name: string;
  email: string;
  role?: string | null;
  slack_username?: string | null;
}

export interface Meeting {
  id: string;
  client_name: string;
  title: string;
  meeting_date?: string | null;
  meeting_time?: string | null;
  description?: string | null;
  status: MeetingStatus;
  created_at: string;
  updated_at: string;
  participants: Participant[];
}

export interface MeetingListItem {
  id: string;
  client_name: string;
  title: string;
  meeting_date?: string | null;
  status: MeetingStatus;
  updated_at: string;
}

export interface Template {
  id: string;
  name: string;
  type: "agenda" | "minutes";
  source: string;
  content: string;
  is_default: boolean;
  can_delete?: boolean;
}

export interface DashboardStats {
  total_meetings: number;
  meetings_this_week: number;
  pending_approval: number;
  completed_meetings: number;
  pending_action_items: number;
  emails_sent: number;
  slack_messages_sent: number;
}

export interface Agenda {
  id: string;
  meeting_id: string;
  content: string;
  version: number;
}

export interface Recording {
  id: string;
  meeting_id: string;
  filename: string;
  mime_type?: string | null;
  source: string;
  size_bytes?: number | null;
  created_at: string;
}

export interface TranscriptSegment {
  speaker?: string;
  start?: number;
  end?: number;
  text: string;
}

export interface Transcript {
  id: string;
  meeting_id: string;
  text: string;
  language?: string | null;
  segments?: TranscriptSegment[] | null;
  provider: string;
  created_at: string;
}

/** Texto utilizável da transcrição (corpo ou segmentos). */
export function transcriptText(tr: Transcript | null | undefined): string {
  if (!tr) return "";
  const body = (tr.text || "").trim();
  if (body) return body;
  const fromSegments = (tr.segments || [])
    .map((s) => (s.text || "").trim())
    .filter(Boolean)
    .join("\n\n");
  return fromSegments.trim();
}

export interface Summary {
  id: string;
  meeting_id: string;
  content: string;
  short_summary?: string | null;
  version: number;
  is_approved: boolean;
  analysis?: Record<string, unknown> | null;
}

export interface EmailLog {
  id: string;
  meeting_id: string;
  distribution_id?: string | null;
  to_email: string;
  subject: string;
  status: string;
  provider: string;
  error?: string | null;
  created_at: string;
}

export interface EmailDistribution {
  id: string;
  meeting_id: string;
  summary_id: string;
  status: string;
  created_at: string;
  completed_at?: string | null;
  logs: EmailLog[];
}

export interface ProcessingJob {
  id: string;
  meeting_id: string;
  job_type: string;
  status: "pending" | "running" | "completed" | "failed";
  result_id?: string | null;
  error?: string | null;
  created_at: string;
  updated_at: string;
}

export async function waitForJob(
  meetingId: string,
  jobId: string,
  getJob: (mid: string, jid: string) => Promise<ProcessingJob>,
  intervalMs = 3000,
  maxAttempts = 1200
): Promise<ProcessingJob> {
  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    const job = await getJob(meetingId, jobId);
    if (job.status === "completed" || job.status === "failed") {
      return job;
    }
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  throw new Error(
    "O processamento demorou demasiado tempo (reuniões longas podem levar mais de 1 hora). Atualiza a página e verifica o estado da reunião."
  );
}

export interface ActionItem {
  id: string;
  meeting_id: string;
  task: string;
  assignee_name?: string | null;
  assignee_slack?: string | null;
  timing?: string | null;
  status: string;
}

export const api = {
  health: () =>
    request<{
      status: string;
      auth_enabled?: boolean;
      meeting_retention_days?: number;
    }>("/api/health"),
    auth: {
      config: () =>
        request<{
          auth_enabled: boolean;
          allow_registration: boolean;
          max_team_users: number;
          allowed_email_domains?: string[];
          password_reset_enabled?: boolean;
          slack_enabled?: boolean;
          slack_default_channel?: string;
        }>("/api/auth/config"),
      register: async (name: string, email: string, password: string) => {
        const result = await request<{
          user: { id: string; name: string; email: string; role: string };
        }>("/api/auth/register", {
          method: "POST",
          body: JSON.stringify({ name, email, password }),
        });
        return result;
      },
      login: async (email: string, password: string) => {
        return request<{
          user: { id: string; name: string; email: string; role: string };
        }>("/api/auth/login", {
          method: "POST",
          body: JSON.stringify({ email, password }),
        });
      },
      forgotPassword: async (email: string) => {
        return request<{ message: string }>("/api/auth/forgot-password", {
          method: "POST",
          body: JSON.stringify({ email }),
        });
      },
      resetPassword: async (token: string, password: string) => {
        return request<{ message: string }>("/api/auth/reset-password", {
          method: "POST",
          body: JSON.stringify({ token, password }),
        });
      },
    me: () =>
      request<{ id: string; name: string; email: string; role: string }>(
        "/api/auth/me"
      ),
    logout: async () => {
      try {
        return await request<{ ok: boolean }>("/api/auth/logout", {
          method: "POST",
        });
      } finally {
        clearSessionToken();
      }
    },
  },
  dashboard: () => request<DashboardStats>("/api/dashboard/stats"),
  meetings: {
    list: () => request<MeetingListItem[]>("/api/meetings"),
    get: (id: string) => request<Meeting>(`/api/meetings/${id}`),
    /** Carrega gravação, transcrição, agenda e ata numa só ronda (SSR + refresh). */
    fetchWorkflow: async (id: string) => {
      const [recordings, transcript, agenda, minutes] = await Promise.all([
        request<Recording[]>(`/api/meetings/${id}/recordings`).catch(
          () => [] as Recording[]
        ),
        request<Transcript | null>(`/api/meetings/${id}/transcript`).catch(
          () => null
        ),
        request<Agenda | null>(`/api/meetings/${id}/agenda`).catch(() => null),
        request<Summary | null>(`/api/meetings/${id}/minutes`).catch(
          () => null
        ),
      ]);
      return { recordings, transcript, agenda, minutes };
    },
    /** Dados da página de reunião — igual para todos os utilizadores (SSR). */
    fetchPageBundle: async (id: string) => {
      const [meeting, recordings, transcript, agenda, minutes, templates] =
        await Promise.all([
          request<Meeting>(`/api/meetings/${id}`),
          request<Recording[]>(`/api/meetings/${id}/recordings`).catch(
            () => [] as Recording[]
          ),
          request<Transcript | null>(`/api/meetings/${id}/transcript`).catch(
            () => null
          ),
          request<Agenda | null>(`/api/meetings/${id}/agenda`).catch(
            () => null
          ),
          request<Summary | null>(`/api/meetings/${id}/minutes`).catch(
            () => null
          ),
          request<Template[]>(`/api/templates`).catch(() => [] as Template[]),
        ]);
      return {
        meeting,
        recordings,
        transcript,
        agenda,
        minutes,
        templates,
      };
    },
    create: (body: unknown) =>
      request<Meeting>("/api/meetings", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    update: (id: string, body: unknown) =>
      request<Meeting>(`/api/meetings/${id}`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),
    delete: (id: string) =>
      request<void>(`/api/meetings/${id}`, { method: "DELETE" }),
    start: (id: string) =>
      request<Meeting>(`/api/meetings/${id}/start`, { method: "POST" }),
    generateAgenda: (id: string, template_id?: string) =>
      request<ProcessingJob>(`/api/meetings/${id}/agenda/generate`, {
        method: "POST",
        body: JSON.stringify({ template_id }),
      }),
    getAgenda: (id: string) =>
      request<Agenda | null>(`/api/meetings/${id}/agenda`),
    updateAgenda: (id: string, content: string) =>
      request<Agenda>(`/api/meetings/${id}/agenda`, {
        method: "PATCH",
        body: JSON.stringify({ content }),
      }),
    getRecordings: (id: string) =>
      request<Recording[]>(`/api/meetings/${id}/recordings`),
    deleteRecording: (meetingId: string, recordingId: string) =>
      request<void>(`/api/meetings/${meetingId}/recordings/${recordingId}`, {
        method: "DELETE",
      }),
    getTranscript: (id: string) =>
      request<Transcript | null>(`/api/meetings/${id}/transcript`),
    deleteTranscript: (id: string) =>
      request<void>(`/api/meetings/${id}/transcript`, { method: "DELETE" }),
    uploadRecording: async (id: string, file: File, source = "upload") => {
      const form = new FormData();
      form.append("file", file);
      const res = await multipartUpload(
        `${uploadPath(`/api/meetings/${id}/recordings?source=${encodeURIComponent(source)}`)}`,
        form
      );
      if (!res.ok) {
        const err = await res.text();
        throw new Error(
          err.includes("Failed to fetch") || err.includes("NetworkError")
            ? "Ligação perdida durante o upload. Mantém a app aberta — ficheiros grandes demoram vários minutos."
            : parseApiError(err || res.statusText)
        );
      }
      return res.json() as Promise<Recording>;
    },
    importGoogleMeet: async (
      id: string,
      file: File,
      mode: "recording" | "transcript" | "auto" = "auto"
    ) => {
      const form = new FormData();
      form.append("file", file);
      form.append("mode", mode);
      const res = await multipartUpload(
        uploadPath(`/api/meetings/${id}/import/google-meet`),
        form
      );
      if (!res.ok) {
        const err = await res.text();
        throw new Error(
          err.includes("Failed to fetch") || err.includes("NetworkError")
            ? "Ligação perdida durante o upload. Mantém a app aberta — ficheiros grandes demoram vários minutos."
            : parseApiError(err || res.statusText)
        );
      }
      return res.json() as Promise<{
        import_type: string;
        message: string;
        recording?: Recording;
      }>;
    },
    transcribe: (id: string) =>
      request<ProcessingJob>(`/api/meetings/${id}/transcribe`, {
        method: "POST",
      }),
    generateMinutes: (id: string, template_id?: string) =>
      request<ProcessingJob>(`/api/meetings/${id}/minutes/generate`, {
        method: "POST",
        body: JSON.stringify({ template_id }),
      }),
    getJob: (id: string, jobId: string) =>
      request<ProcessingJob>(`/api/meetings/${id}/jobs/${jobId}`),
    getMinutes: (id: string) =>
      request<Summary | null>(`/api/meetings/${id}/minutes`),
    updateMinutes: (id: string, content: string) =>
      request<Summary>(`/api/meetings/${id}/minutes`, {
        method: "PATCH",
        body: JSON.stringify({ content }),
      }),
    exportMinutesDocx: (id: string, content: string) =>
      downloadPostFile(
        `/api/meetings/${id}/minutes/export/docx`,
        "ata-rascunho.docx",
        { content }
      ),
    exportAgendaDocx: (id: string, content: string) =>
      downloadPostFile(
        `/api/meetings/${id}/agenda/export/docx`,
        "agenda.docx",
        { content }
      ),
    approve: (id: string, summary_id: string) =>
      request<unknown>(`/api/meetings/${id}/approve`, {
        method: "POST",
        body: JSON.stringify({ summary_id }),
      }),
    distributeEmail: (id: string, idempotencyKey: string, forceResend = false) =>
      request<EmailDistribution>(`/api/meetings/${id}/distribute/email`, {
        method: "POST",
        headers: { "Idempotency-Key": idempotencyKey },
        body: JSON.stringify({
          idempotency_key: idempotencyKey,
          force_resend: forceResend,
        }),
      }),
    getEmailDistribution: (id: string, distributionId: string) =>
      request<EmailDistribution>(
        `/api/meetings/${id}/distributions/${distributionId}`
      ),
    getEmailLogs: (id: string, distributionId?: string) =>
      request<EmailLog[]>(
        `/api/meetings/${id}/email-logs${
          distributionId ? `?distribution_id=${encodeURIComponent(distributionId)}` : ""
        }`
      ),
    slackPreview: (id: string) =>
      request<{ channel: string; message: string }>(
        `/api/meetings/${id}/slack/preview`
      ),
    slackSend: (id: string) =>
      request<{ id: string; channel: string; status: string; error?: string | null }>(
        `/api/meetings/${id}/slack/send`,
        {
          method: "POST",
          body: JSON.stringify({}),
        }
      ),
    actionItems: (id: string) =>
      request<ActionItem[]>(`/api/meetings/${id}/action-items`),
    addParticipant: (id: string, body: unknown) =>
      request<Participant>(`/api/meetings/${id}/participants`, {
        method: "POST",
        body: JSON.stringify(body),
      }),
    importParticipants: (id: string, participants: unknown[]) =>
      request<Participant[]>(`/api/meetings/${id}/participants/import`, {
        method: "POST",
        body: JSON.stringify({ participants }),
      }),
  },
  templates: {
    list: (type?: string) =>
      request<Template[]>(
        `/api/templates${type ? `?type=${type}` : ""}`
      ),
    upload: async (name: string, type: string, file: File) => {
      const form = new FormData();
      form.append("file", file);
      const res = await multipartUpload(
        uploadPath(
          `/api/templates/upload?name=${encodeURIComponent(name)}&type=${type}`
        ),
        form
      );
      if (!res.ok) throw new Error(await res.text());
      return res.json() as Promise<Template>;
    },
    setDefault: (id: string) =>
      request<Template>(`/api/templates/${id}/set-default`, { method: "POST" }),
    refreshContent: (id: string) =>
      request<Template>(`/api/templates/${id}/refresh-content`, {
        method: "POST",
      }),
    delete: (id: string) =>
      request<void>(`/api/templates/${id}`, { method: "DELETE" }),
    cleanupCopies: () =>
      request<{ ok: boolean; removed: number }>(
        "/api/templates/cleanup-copies",
        { method: "POST" }
      ),
  },
};

export { formatBytes };

export const STATUS_LABELS: Record<MeetingStatus, string> = {
  draft: "Rascunho",
  agenda_ready: "Agenda pronta",
  in_progress: "Em curso",
  recorded: "Gravada",
  processing: "A processar",
  minutes_ready: "Ata gerada",
  pending_approval: "Aguarda aprovação",
  approved: "Aprovada",
  distributed: "Distribuída",
};
