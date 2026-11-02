import Link from "next/link";

export default function ForbiddenPage() {
  return <main className="flex min-h-screen items-center justify-center bg-[#f3f5f9] px-5 py-10 text-[#172b4d]">
    <section role="alert" className="w-full max-w-lg rounded-2xl border border-[#e1e7f0] bg-white p-8 text-center shadow-sm">
      <h1 className="text-xl font-semibold">Sin permiso</h1>
      <p className="mt-2 text-sm leading-6 text-[#647b9d]">No tienes permiso para acceder a esta sección. Si necesitas acceso, comunícate con un administrador.</p>
      <Link href="/" className="mt-6 inline-flex rounded-lg bg-[#2864ed] px-4 py-2 text-sm font-medium text-white">Volver al panel</Link>
    </section>
  </main>;
}
