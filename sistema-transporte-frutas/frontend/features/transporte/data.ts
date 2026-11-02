"use client";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
export type City={id_ciudad:number;nombre:string};
export type Stage={id:string;carga_id:string;viaje_id:string;viaje_codigo:string;orden:number;origen_id:number;destino_id:number;origen:string;destino:string;estado:string;salida_real?:string;llegada_real?:string};
export type Load={id:string;codigo:string;cliente_id:string;producto:string;variedad?:string;cantidad:number;unidad:string;peso_neto_total_kg?:string;peso_bruto_total_kg?:string;procedencia:string;destino:string;origen_id:number;destino_id:number;estado:string;etapas:Stage[];jabas_despachadas:number;[key:string]:unknown};
export type Route={id:string;codigo:string;nombre:string;origen_id:number;destino_id:number;paradas:{ciudad_id:number;orden:number;tiempo_espera:number}[]};
export type Trip={flete_centimos?:number;id:string;codigo:string;ruta_id:string;vehiculo_id:string;conductor_id:string;estado:string;fecha_salida_programada:string;fecha_entrega_estimada:string;cargas_ids:string[];etapas:Stage[];peso_total_kg:string;capacidad_kg:number};
export type Person={id:string;nombre:string;placa:string;estado:string;capacidad_kg:number;tiene_remolque?:boolean;placa_remolque?:string};
export async function all<T>(path:string):Promise<T[]>{const first=(await api.get<{items:T[];pages:number}|T[]>(path,{params:{page:1,page_size:100}})).data;if(Array.isArray(first))return first;const result=[...first.items];for(let page=2;page<=first.pages;page++)result.push(...(await api.get<{items:T[]}>(path,{params:{page,page_size:100}})).data.items);return result;}
export function useCatalog<T>(resource:string,options:{refetchInterval?:number}={}){return useQuery({queryKey:[resource,"transport-catalog"],queryFn:()=>all<T>("/"+resource),...options});}
export function path(route?:Route){return route?[route.origen_id,...route.paradas.map(p=>p.ciudad_id),route.destino_id]:[];}
export const control="mt-1 w-full rounded-lg border border-[#dce4df] bg-white px-3 py-2 text-sm";
