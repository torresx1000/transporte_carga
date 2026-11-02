export function ModulePlaceholder({ title, description }: { title: string; description: string }) {
  return (
    <main className="min-h-screen bg-[#f7f8fa] px-6 py-10 text-[#17211e] sm:px-10">
      <div className="mx-auto max-w-6xl">
        <p className="mb-2 text-xs text-[#87918c]">Administración</p>
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        <p className="mt-1 text-sm text-[#7a8580]">{description}</p>
        <div className="mt-7 rounded-xl border border-[#e8ece9] bg-white p-8 text-sm text-[#89938e]">
          Este módulo estará disponible próximamente.
        </div>
      </div>
    </main>
  );
}
