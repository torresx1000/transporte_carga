import { RefreshCw, Search } from "lucide-react";

export function TableSkeleton({ rows = 5, columns = 6 }: { rows?: number; columns?: number }) {
  return <div aria-label="Cargando datos" className="animate-pulse space-y-3 p-5">{Array.from({ length: rows }, (_, row) => <div key={row} className="flex gap-4">{Array.from({ length: columns }, (_, col) => <div key={col} className={`h-8 rounded bg-[#eef1ef] ${col === 0 ? "w-40" : "flex-1"}`} />)}</div>)}</div>;
}

export function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  const forbidden = message === "No tienes permiso para esta acción";
  return <div role="alert" className="flex flex-col items-center px-5 py-12 text-center"><p className="text-sm font-medium text-[#4a554f]">{forbidden ? "Sin permiso" : "No se pudieron cargar los datos"}</p><p className="mt-1 max-w-md text-xs text-[#89938e]">{message}</p>{!forbidden && <button onClick={onRetry} className="mt-4 inline-flex items-center gap-2 rounded-lg border border-[#e2e8e3] px-3 py-2 text-xs font-medium text-[#536058]"><RefreshCw size={13}/>Reintentar</button>}</div>;
}

export function EmptyState({ title = "No hay registros", description = "Cuando existan datos, aparecerán aquí.", action }: { title?: string; description?: string; action?: React.ReactNode }) {
  return <div className="flex flex-col items-center px-5 py-12 text-center"><span className="mb-3 flex size-10 items-center justify-center rounded-full bg-[#f1f4f2] text-[#929d97]"><Search size={18}/></span><p className="text-sm font-medium text-[#46524b]">{title}</p><p className="mt-1 text-xs text-[#89938e]">{description}</p>{action && <div className="mt-4">{action}</div>}</div>;
}
