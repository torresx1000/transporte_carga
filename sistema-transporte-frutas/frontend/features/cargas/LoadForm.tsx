"use client";
import { useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { loadFieldErrors, validateLoadForm, type FieldErrors } from "./validation";
import { getApiError } from "@/lib/api/errors";
import { City, Load, Person, useCatalog, control } from "@/features/transporte/data";
import { ErrorState, TableSkeleton } from "@/components/ui/AsyncStates";

export default function LoadForm(){
 const id=useSearchParams().get("editar")||"";
 const detail=useQuery({queryKey:["cargas","edit",id],enabled:!!id,queryFn:async()=>(await api.get<Load>("/cargas/"+id)).data});
 if(id&&detail.isLoading)return <TableSkeleton/>;
 if(id&&detail.isError)return <ErrorState message={getApiError(detail.error)} onRetry={()=>void detail.refetch()}/>;
 return <Editor key={id} initial={detail.data}/>;
}
function Editor({initial}:{initial?:Load}){
 const router=useRouter();const cache=useQueryClient();
 const clients=useCatalog<Person>("clientes"),cities=useCatalog<City>("ciudades");
 const [files,setFiles]=useState<File[]>([]),[busy,setBusy]=useState(false),[error,setError]=useState("");
 const formRef=useRef<HTMLFormElement>(null);
 const [fieldErrors,setFieldErrors]=useState<FieldErrors>({});
 function focusError(errors:FieldErrors){requestAnimationFrame(()=>{const element=formRef.current?.elements.namedItem(Object.keys(errors)[0]);if(element instanceof HTMLElement){element.scrollIntoView({behavior:"smooth",block:"center"});element.focus({preventScroll:true});}});}
 function fieldProps(key:string){return {id:`carga-${key}`,"aria-invalid":!!fieldErrors[key],"aria-describedby":fieldErrors[key]?`error-${key}`:undefined,className:control+(fieldErrors[key]?" !border-red-600 !bg-red-50 outline-red-600 ring-1 ring-red-600":""),onChange:()=>setFieldErrors(current=>{const next={...current};delete next[key];return next;})};}
 function fieldError(key:string){return fieldErrors[key]?<span id={`error-${key}`} role="alert" className="mt-1 block text-xs font-medium text-red-700">{fieldErrors[key]}</span>:null;}
 const [savedId,setSavedId]=useState(initial?.id||"");
 async function submit(event:React.FormEvent<HTMLFormElement>){
  event.preventDefault();if(busy)return;setError("");const invalid=validateLoadForm(event.currentTarget);setFieldErrors(invalid);if(Object.keys(invalid).length){focusError(invalid);return;}setBusy(true);
  const data=Object.fromEntries(new FormData(event.currentTarget).entries());
  const numeric=new Set(["origen_id","destino_id","cantidad","jabas_despachadas","peso_neto_total_kg","peso_bruto_total_kg","temperatura"]);
  const payload:Record<string,unknown>={};
  for(const [key,value]of Object.entries(data)){if(value===""){if(["peso_neto_total_kg","peso_bruto_total_kg","temperatura","fecha_recojo","fecha_entrega"].includes(key))payload[key]=null;continue;}payload[key]=numeric.has(key)?Number(value):value;}
  payload.procedencia=cities.data?.find(c=>c.id_ciudad===payload.origen_id)?.nombre;
  payload.destino=cities.data?.find(c=>c.id_ciudad===payload.destino_id)?.nombre;
  try{
   let id=savedId;
   if(id)await api.patch("/cargas/"+id,payload);else{id=(await api.post<Load>("/cargas",payload)).data.id;setSavedId(id);}
   for(const file of files){const form=new FormData();form.append("archivo",file);await api.post("/cargas/"+id+"/documentos",form);setFiles(current=>current.filter(item=>item!==file));}
   await cache.invalidateQueries({queryKey:["cargas"]});router.push("/cargas/"+id);
  }catch(cause){const invalid=loadFieldErrors(cause);const visible=Object.fromEntries(Object.entries(invalid).filter(([key])=>formRef.current?.elements.namedItem(key)));setFieldErrors(visible);if(Object.keys(visible).length){setError("Revisa los campos marcados en rojo.");focusError(visible);}else setError(getApiError(cause));}finally{setBusy(false);}
 }
 function input(key:string,label:string,type="text",required=false){return <label key={key} className="text-sm">{label}{required?" *":""}<input name={key} type={type} required={required} defaultValue={String(initial?.[key]??(key==="cantidad"?1:key==="jabas_despachadas"?0:""))} {...fieldProps(key)} max={key==="temperatura"?100:undefined} min={type==="number"?(key==="temperatura"?-100:key==="cantidad"?1:["peso_neto_total_kg","peso_bruto_total_kg"].includes(key)?0.001:0):undefined} step={type==="number"?(key==="cantidad"||key==="jabas_despachadas"?"1":"0.001" ):undefined}/>{fieldError(key)}</label>;}
 const unavailable=clients.isError||cities.isError;
 if(clients.isLoading||cities.isLoading)return <TableSkeleton/>;
 return <main className="min-h-screen bg-[#f7f8fa] p-6"><div className="mx-auto max-w-4xl"><button onClick={()=>router.push("/cargas")} className="mb-4 text-sm text-[#2563EB]">← Cargas</button><h1 className="text-2xl font-semibold">{initial?"Editar carga":"Nueva carga"}</h1><p className="mt-2 text-sm">Registra el envío una sola vez. El código se genera con la fecha de recojo y las ciudades de origen y destino.</p><form ref={formRef} noValidate onSubmit={submit} className="mt-6 space-y-6 rounded-xl bg-white p-6"><fieldset disabled={busy} className="grid gap-4 sm:grid-cols-2"><legend className="mb-3 font-semibold">Identificación</legend><label className="text-sm">Cliente *<select name="cliente_id" required defaultValue={initial?.cliente_id??""} {...fieldProps("cliente_id")}><option value="">Selecciona cliente</option>{clients.data?.filter(c=>["activo","activa"].includes(c.estado)||c.id===initial?.cliente_id).map(c=><option key={c.id} value={c.id}>{c.nombre}</option>)}</select>{fieldError("cliente_id")}</label>{input("contacto","Persona de contacto")}{input("telefono","Teléfono")}{input("destinatario","Destinatario")}<p className="self-end py-2 text-xs text-gray-500">Fecha de registro: {initial?.created_at?String(initial.created_at):"Se registra automáticamente al guardar"}</p></fieldset>
 <fieldset disabled={busy} className="grid gap-4 sm:grid-cols-2"><legend className="mb-3 font-semibold">Producto y cantidades</legend>{input("producto","Tipo de fruta","text",true)}{input("variedad","Variedad")}{input("cantidad","Cantidad","number",true)}<label className="text-sm">Unidad<select name="unidad" defaultValue={initial?.unidad||"jaba"} {...fieldProps("unidad")}>{["jaba","caja","kg"].map(u=><option key={u}>{u}</option>)}</select>{fieldError("unidad")}</label>{input("presentacion","Presentación")}{input("jabas_despachadas","Jabas despachadas","number")}{input("peso_neto_total_kg","Peso neto total (kg)","number")}{input("peso_bruto_total_kg","Peso bruto total (kg)","number")}</fieldset>
 {(["origen","destino"]as const).map(side=><fieldset disabled={busy} key={side} className="grid gap-4 sm:grid-cols-2"><legend className="mb-3 font-semibold">{side==="origen"?"Procedencia / recojo":"Destino / entrega"}</legend><label className="text-sm">Ciudad / localidad *<select name={side+"_id"} required defaultValue={String(initial?.[side+"_id"]??"")} {...fieldProps(side+"_id")}><option value="">Selecciona una ciudad</option>{cities.data?.map(c=><option key={c.id_ciudad} value={c.id_ciudad}>{c.nombre}</option>)}</select>{fieldError(side+"_id")}</label>{input(side+"_departamento","Departamento")}{input(side+"_provincia","Provincia")}{input(side+"_distrito","Distrito")}{input(side+"_direccion",side==="origen"?"Dirección / punto de recojo":"Dirección / punto de entrega")}</fieldset>)}
 <fieldset disabled={busy} className="grid gap-4 sm:grid-cols-2"><legend className="mb-3 font-semibold">Condiciones</legend>{input("fecha_recojo","Fecha de recojo","date")}{input("fecha_entrega","Fecha requerida de entrega","date")}{input("temperatura","Temperatura (°C)","number")}<label className="text-sm">Prioridad<select name="prioridad" defaultValue={String(initial?.prioridad??"normal")} {...fieldProps("prioridad")}>{["baja","normal","alta","urgente"].map(p=><option key={p}>{p}</option>)}</select>{fieldError("prioridad")}</label><label className="text-sm sm:col-span-2">Observaciones<textarea name="observaciones" rows={3} defaultValue={String(initial?.observaciones??"")} {...fieldProps("observaciones")}/>{fieldError("observaciones")}</label></fieldset>
 <section><h2 className="font-semibold">Documentos</h2><p className="mt-1 text-sm text-gray-600">PDF, JPG, PNG, WEBP, DOCX o XLSX. Máximo 10 MB por archivo. Se almacenan en el servidor después de guardar la carga.</p><input type="file" multiple disabled={busy} accept=".pdf,.jpg,.jpeg,.png,.webp,.docx,.xlsx" className="mt-3 text-sm" onChange={event=>setFiles(Array.from(event.target.files??[]))}/><ul className="mt-2 text-sm">{files.map((f,i)=><li key={i}>{f.name}</li>)}</ul></section>
 {savedId&&!initial&&<p className="rounded bg-blue-50 p-3 text-sm">La carga ya está guardada. Si hubo un error de archivo, puedes reintentar sin duplicarla.</p>}{error&&<p role="alert" className="rounded bg-red-50 p-3 text-sm text-red-700">{error}</p>}{unavailable&&<p role="alert" className="text-red-700">No se pudo cargar el catálogo. <button type="button" onClick={()=>{void cities.refetch();void clients.refetch()}}>Reintentar</button></p>}{cities.isSuccess&&!cities.data.length&&<p className="text-sm">Registra primero las ciudades desde Rutas.</p>}<footer className="flex justify-end gap-3"><button type="button" onClick={()=>router.push("/cargas")} disabled={busy} className="rounded border px-4 py-2">Cancelar</button><button disabled={busy||unavailable||cities.isLoading||clients.isLoading} className="rounded bg-[#2563EB] px-4 py-2 text-white disabled:opacity-50">{busy?"Guardando…":"Guardar carga"}</button></footer></form></div></main>;
}
