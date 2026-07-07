import { NextRequest, NextResponse } from "next/server";

const AUTH_COOKIE = "sync2meet_token";

export function backendBase(): string {
  return (
    process.env.INTERNAL_API_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    "http://127.0.0.1:8000"
  ).replace(/\/$/, "");
}

/** Proxy multipart upload to FastAPI using HttpOnly cookie (token never exposed to JS). */
export async function proxyMultipartUpload(
  request: NextRequest,
  backendPath: string
): Promise<NextResponse> {
  const token = request.cookies.get(AUTH_COOKIE)?.value;
  if (!token) {
    return NextResponse.json(
      { detail: "Sessão expirada. Inicia sessão novamente." },
      { status: 401 }
    );
  }

  const contentType = request.headers.get("content-type");
  const headers: Record<string, string> = {
    Authorization: `Bearer ${token}`,
  };
  if (contentType) {
    headers["Content-Type"] = contentType;
  }

  const backendRes = await fetch(`${backendBase()}${backendPath}`, {
    method: "POST",
    headers,
    body: request.body,
    duplex: "half",
  } as RequestInit);

  const raw = await backendRes.text();
  return new NextResponse(raw, {
    status: backendRes.status,
    headers: {
      "Content-Type":
        backendRes.headers.get("content-type") || "application/json",
    },
  });
}
