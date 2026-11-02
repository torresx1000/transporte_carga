import LoadDetail from "@/features/cargas/LoadDetail";

export default async function Page({ params }: PageProps<"/cargas/[id]">) {
  const { id } = await params;
  return <LoadDetail id={id} />;
}
