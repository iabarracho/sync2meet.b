import type { NextRequest } from "next/server";
import { proxyAuthPost } from "@/lib/auth-proxy";

export async function POST(request: NextRequest) {
  return proxyAuthPost(request, "register");
}
