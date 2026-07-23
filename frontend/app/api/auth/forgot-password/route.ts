import { NextRequest, NextResponse } from "next/server";

function backendBase(): string {
  return (
    process.env.INTERNAL_API_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    "http://127.0.0.1:8000"
  ).replace(/\/$/, "");
}

/** Proxy forgot/reset password to backend at request time (not build-time rewrite). */
async function proxyPasswordReset(
  request: NextRequest,
  path: "forgot-password" | "reset-password"
): Promise<NextResponse> {
  const backendRes = await fetch(`${backendBase()}/api/auth/${path}`, {
    method: "POST",
    headers: {
      "Content-Type":
        request.headers.get("content-type") || "application/json",
    },
    body: await request.text(),
    cache: "no-store",
  });
  const raw = await backendRes.text();
  return new NextResponse(raw, {
    status: backendRes.status,
    headers: {
      "Content-Type":
        backendRes.headers.get("content-type") || "application/json",
    },
  });
}

export async function POST(request: NextRequest) {
  return proxyPasswordReset(request, "forgot-password");
}
