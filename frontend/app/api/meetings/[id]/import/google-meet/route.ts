import type { NextRequest } from "next/server";
import { proxyMultipartUpload } from "@/lib/upload-proxy";

export const runtime = "nodejs";
export const maxDuration = 3600;

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  return proxyMultipartUpload(
    request,
    `/api/meetings/${id}/import/google-meet`
  );
}
