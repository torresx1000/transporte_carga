import { NextResponse } from "next/server";

export async function POST() {
  const response = NextResponse.json({ ok: true });
  for (const name of ["tf_refresh", "tf_session", "tf_role"]) response.cookies.set(name, "", { httpOnly: true, path: "/", maxAge: 0 });
  return response;
}
