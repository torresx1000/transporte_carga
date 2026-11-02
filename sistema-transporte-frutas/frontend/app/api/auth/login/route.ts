import { NextResponse } from "next/server";

 const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
//const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "https://transporte-carga.onrender.com";

export async function POST(request: Request) {
  const body = await request.json() as { email?: string; password?: string };
  const form = new URLSearchParams({ username: body.email ?? "", password: body.password ?? "" });
  const upstream = await fetch(`${apiUrl}/auth/login`, { method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" }, body: form, cache: "no-store" });
  const data = await upstream.json().catch(() => ({}));
  if (!upstream.ok) return NextResponse.json(data, { status: upstream.status });
  const response = NextResponse.json({ access_token: data.access_token, user: data.user });
  const cookieOptions = { httpOnly: true, secure: process.env.NODE_ENV === "production", sameSite: "lax" as const, path: "/" };
  response.cookies.set("tf_refresh", data.refresh_token, { ...cookieOptions, maxAge: 60 * 60 * 24 * 7 });
  response.cookies.set("tf_session", "1", { ...cookieOptions, maxAge: 60 * 60 * 24 * 7 });
  response.cookies.set("tf_role", data.user?.role ?? "", { ...cookieOptions, maxAge: 60 * 60 * 24 * 7 });
  return response;
}
