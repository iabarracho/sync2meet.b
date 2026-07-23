import { NextRequest, NextResponse } from "next/server";

const AUTH_COOKIE = "sync2meet_token";

function cookieMaxAgeSeconds(): number {
  const raw =
    process.env.AUTH_TOKEN_HOURS ??
    process.env.NEXT_PUBLIC_AUTH_TOKEN_HOURS ??
    "24";
  const hours = Number.parseInt(raw, 10);
  if (!Number.isFinite(hours) || hours <= 0) {
    return 24 * 60 * 60;
  }
  return hours * 60 * 60;
}

function backendBase(): string {
  return (
    process.env.INTERNAL_API_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    "http://127.0.0.1:8000"
  ).replace(/\/$/, "");
}

function cookieSecure(): boolean {
  const publicUrl =
    process.env.APP_PUBLIC_URL ||
    process.env.NEXT_PUBLIC_APP_PUBLIC_URL ||
    "";
  // Só Secure em HTTPS — evita cookies invisíveis em http://127.0.0.1
  return publicUrl.startsWith("https://");
}

function cookieOptions() {
  return {
    httpOnly: true,
    sameSite: "lax" as const,
    path: "/",
    maxAge: cookieMaxAgeSeconds(),
    secure: cookieSecure(),
  };
}

/** Extrai sync2meet_token dos headers Set-Cookie do backend. */
function tokenFromResponseHeaders(headers: Headers): string | null {
  const getSetCookie = (headers as Headers & { getSetCookie?: () => string[] })
    .getSetCookie;
  if (typeof getSetCookie === "function") {
    for (const cookie of getSetCookie.call(headers)) {
      const token = tokenFromSetCookie(cookie);
      if (token) return token;
    }
  }
  return (
    tokenFromSetCookie(headers.get("set-cookie")) ??
    tokenFromSetCookie(headers.get("Set-Cookie"))
  );
}

/** Extrai sync2meet_token de um header Set-Cookie individual. */
function tokenFromSetCookie(setCookie: string | null): string | null {
  if (!setCookie) return null;
  const match = setCookie.match(/sync2meet_token=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}

/** Proxy auth POST to backend and set/clear session cookie on the Next.js origin. */
export async function proxyAuthPost(
  request: NextRequest,
  path: "login" | "register" | "logout"
): Promise<NextResponse> {
  const headers: Record<string, string> = {
    "Content-Type": request.headers.get("content-type") || "application/json",
  };
  const cookie = request.headers.get("cookie");
  if (cookie) headers.Cookie = cookie;

  const backendRes = await fetch(`${backendBase()}/api/auth/${path}`, {
    method: "POST",
    headers,
    body: await request.text(),
    cache: "no-store",
  });

  const raw = await backendRes.text();
  let data: { user?: unknown; ok?: boolean };
  try {
    data = JSON.parse(raw) as { user?: unknown; ok?: boolean };
  } catch {
    return new NextResponse(raw, {
      status: backendRes.status,
      headers: {
        "Content-Type": backendRes.headers.get("content-type") || "text/plain",
      },
    });
  }

  const response = NextResponse.json(data, { status: backendRes.status });

  if (path === "logout" && backendRes.ok) {
    response.cookies.delete(AUTH_COOKIE);
    return response;
  }

  const token = tokenFromResponseHeaders(backendRes.headers);

  if (backendRes.ok && token) {
    response.cookies.set(AUTH_COOKIE, token, cookieOptions());
  }

  return response;
}
