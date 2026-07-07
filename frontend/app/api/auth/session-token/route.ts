import type { NextRequest } from "next/server";

import { NextResponse } from "next/server";



/** Removido: o token não deve ser exposto ao JavaScript. Uploads usam proxy server-side. */

export async function GET(_request: NextRequest) {

  return NextResponse.json(

    { detail: "Endpoint descontinuado. Usa cookies HttpOnly." },

    { status: 410 }

  );

}

