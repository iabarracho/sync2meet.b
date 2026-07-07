import type { EmailLog } from "@/lib/api";

const STORAGE_PREFIX = "sync2meet-email-sent:";

export type EmailSentResult = {
  distributionId: string;
  emails: string[];
  sentAt: string;
};

export function emailSentStorageKey(meetingId: string): string {
  return `${STORAGE_PREFIX}${meetingId}`;
}

export function saveEmailSentResult(
  meetingId: string,
  result: EmailSentResult
): void {
  if (typeof window === "undefined") return;
  sessionStorage.setItem(emailSentStorageKey(meetingId), JSON.stringify(result));
}

export function readEmailSentResult(
  meetingId: string,
  distributionId?: string | null
): EmailSentResult | null {
  if (typeof window === "undefined") return null;
  const raw = sessionStorage.getItem(emailSentStorageKey(meetingId));
  if (!raw) return null;
  try {
    const data = JSON.parse(raw) as EmailSentResult;
    if (!Array.isArray(data.emails) || !data.distributionId) return null;
    if (distributionId && data.distributionId !== distributionId) return null;
    return data;
  } catch {
    return null;
  }
}

export function emailsFromLogs(logs: EmailLog[]): string[] {
  return logs.filter((log) => log.status === "sent").map((log) => log.to_email);
}
