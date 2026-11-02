"use client";
import { useState } from "react";
import { createPortal } from "react-dom";
import { Trash2 } from "lucide-react";
import { useAuthStore } from "@/lib/auth/authStore";
import { useResourceDelete } from "@/hooks/useResources";
import { getApiError } from "@/lib/api/errors";
import type { ResourceName } from "@/services/resource.service";
export default function DeleteRecordButton({resource,id}:{resource:ResourceName;id?:string}) {
 const role=useAuthStore(s=>s.user?.role); const mutation=useResourceDelete(resource); const [open,setOpen]=useState(false); const [error,setError]=useState("");
 if(role!=="admin" || !id)return null;
 async function remove(){if(!id||mutation.isPending)return;setError("");try{await mutation.mutateAsync(id);setOpen(false)}catch(cause){setError(getApiError(cause))}}
 return <><button type="button" title="Eliminar" aria-label="Eliminar registro" onClick={()=>{setError("");setOpen(true)}} className="rounded-md p-2 text-[#7c8781] hover:bg-red-50 hover:text-red-700"><Trash2 size={15}/></button>{open&&createPortal(<div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"><section role="dialog" aria-modal="true" aria-label="Confirmar eliminación" className="w-full max-w-sm rounded-xl bg-white p-6 shadow-xl"><h2 className="font-semibold">¿Eliminar este registro?</h2><p className="mt-2 text-sm">Se dará de baja y dejará de aparecer en los listados activos. Su información se conservará.</p>{error&&<p role="alert" className="mt-3 text-sm text-red-700">{error}</p>}<div className="mt-6 flex justify-end gap-2"><button disabled={mutation.isPending} onClick={()=>setOpen(false)} className="rounded-lg border px-4 py-2">Cancelar</button><button disabled={mutation.isPending} onClick={()=>void remove()} className="rounded-lg bg-red-700 px-4 py-2 text-white disabled:opacity-50">{mutation.isPending?"Eliminando…":"Eliminar"}</button></div></section></div>,document.body)}</>;
}
