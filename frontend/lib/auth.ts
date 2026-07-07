/** Cookie HttpOnly é gerido pelo servidor — não guardar JWT em JavaScript. */



export function saveSessionToken(_token: string): void {

  /* noop — segurança */

}



export function getSessionBearer(): string | null {

  return null;

}



export function clearSessionToken(): void {

  if (typeof window === "undefined") return;

  sessionStorage.removeItem("sync2meet_bearer");

  localStorage.removeItem("sync2meet_token");

}



/** @deprecated */

export function saveToken(token: string): void {

  saveSessionToken(token);

}



export function clearToken(): void {

  clearSessionToken();

}



export function getToken(): string | null {

  return getSessionBearer();

}



export function authEnabled(): boolean {

  return process.env.NEXT_PUBLIC_AUTH_ENABLED !== "false";

}



export function safeNextPath(raw: string | null): string {

  if (!raw || !raw.startsWith("/") || raw.startsWith("//") || raw.includes("\\")) {

    return "/";

  }

  return raw;

}

