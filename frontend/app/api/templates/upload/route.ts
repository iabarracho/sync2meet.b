import type { NextRequest } from "next/server";
import { proxyMultipartUpload } from "@/lib/upload-proxy";

export const runtime = "nodejs";
export const maxDuration = 300;

export async function POST(request: NextRequest) {
  const name = request.nextUrl.searchParams.get("name") || "";
  const type = request.nextUrl.searchParams.get("type") || "agenda";
  const qs = `?name=${encodeURIComponent(name)}&type=${encodeURIComponent(type)}`;
  return proxyMultipartUpload(request, `/api/templates/upload${qs}`);
}
