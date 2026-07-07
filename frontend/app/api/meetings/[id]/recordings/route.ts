import type { NextRequest } from "next/server";
import { proxyMultipartUpload } from "@/lib/upload-proxy";

export const runtime = "nodejs";
export const maxDuration = 3600;

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const source = request.nextUrl.searchParams.get("source") || "upload";
  const qs = `?source=${encodeURIComponent(source)}`;
  return proxyMultipartUpload(request, `/api/meetings/${id}/recordings${qs}`);
}
