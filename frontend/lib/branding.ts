/** Nome visível no separador do browser, menu lateral e títulos. */
export const APP_NAME =
  process.env.NEXT_PUBLIC_APP_NAME?.trim() || "Sync2meet - BocàBoca";

/** Subtítulo curto (sidebar, meta description). */
export const APP_TAGLINE =
  process.env.NEXT_PUBLIC_APP_TAGLINE?.trim() ||
  "Agendas, atas e distribuição automática";

export function pageTitle(section?: string): string {
  return section ? `${section} · ${APP_NAME}` : APP_NAME;
}
