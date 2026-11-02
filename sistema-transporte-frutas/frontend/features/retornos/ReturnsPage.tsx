import ResourceWorkspace from "@/features/operaciones/ResourceWorkspace";
export default function ReturnsPage({ initialForm = false }: { initialForm?: boolean }) { return <ResourceWorkspace resource="retornos" initialForm={initialForm} />; }
