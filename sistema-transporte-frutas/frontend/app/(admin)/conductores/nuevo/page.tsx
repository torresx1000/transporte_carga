import SchemaResourceWorkspace from "@/features/operaciones/SchemaResourceWorkspace";

export default async function Page({ searchParams }: { searchParams: Promise<{ editar?: string | string[] }> }) {
  const params = await searchParams;
  const editId = Array.isArray(params.editar) ? params.editar[0] ?? "" : params.editar ?? "";
  return <SchemaResourceWorkspace resource="conductores" initialForm editId={editId} />;
}
