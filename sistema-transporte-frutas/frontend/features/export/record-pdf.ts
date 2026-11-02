import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";

type Info = Record<string, unknown>;
const value = (v: unknown) => v === undefined || v === null || v === "" ? "—" : String(v);
const blue = [61, 105, 143] as [number, number, number];

function base(title: string, code: unknown, date: unknown, orientation: "portrait" | "landscape" = "portrait") {
  const doc = new jsPDF({ format: "a4", unit: "mm", orientation });
  const pageWidth = doc.internal.pageSize.getWidth();
  doc.setFillColor(...blue); doc.roundedRect(14, 13, 18, 18, 2, 2, "F");
  doc.setTextColor(255,255,255); doc.setFont("helvetica","bold"); doc.setFontSize(12); doc.text("TF", 19, 24);
  doc.setTextColor(31,41,51); doc.setFontSize(22); doc.text(title, pageWidth - 14, 23, { align:"right" });
  doc.setFontSize(9); doc.setFont("helvetica","normal"); doc.text(`NÚMERO: ${value(code)}`,pageWidth - 14,30,{align:"right"}); doc.text(`FECHA: ${value(date)}`,pageWidth - 14,35,{align:"right"});
  doc.setDrawColor(...blue); doc.line(14,39,pageWidth - 14,39);
  return doc;
}
function section(doc: jsPDF, title: string, y: number) { doc.setFillColor(239,244,248);doc.rect(14,y,182,8,"F");doc.setDrawColor(130,150,166);doc.rect(14,y,182,8);doc.setFont("helvetica","bold");doc.setFontSize(10);doc.setTextColor(35,48,60);doc.text(title,17,y+5.5);return y+12; }
function facts(doc: jsPDF, pairs: [string, unknown][], y: number, cols=2) {
  const width=182/cols, rows=Math.ceil(pairs.length/cols), height=12;
  pairs.forEach(([label,val],i)=>{const x=14+(i%cols)*width, yy=y+Math.floor(i/cols)*height;doc.setDrawColor(160,174,184);doc.rect(x,yy,width,height);doc.setFont("helvetica","bold");doc.setFontSize(8);doc.text(label.toUpperCase(),x+3,yy+4);doc.setFont("helvetica","normal");doc.text(value(val).slice(0,60),x+3,yy+9);});
  return y+rows*height+7;
}
function finish(doc: jsPDF, filename: string, signatures = true) { const pages=doc.getNumberOfPages(), pageWidth=doc.internal.pageSize.getWidth(), pageHeight=doc.internal.pageSize.getHeight(), center=pageWidth/2; for(let p=1;p<=pages;p++){doc.setPage(p);doc.setFontSize(8);doc.setTextColor(100);if(signatures){const lineY=pageHeight-26;doc.text("Firma de conformidad                                      Firma del transportista",center,pageHeight-19,{align:"center"});doc.line(20,lineY,center-20,lineY);doc.line(center+20,lineY,pageWidth-20,lineY);}doc.text(`Página ${p} de ${pages}`,center,pageHeight-10,{align:"center"});} doc.save(filename); }

function dateStamp() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,"0")}-${String(now.getDate()).padStart(2,"0")}`;
}

export function exportRoutesPdf(routes: Info[]) {
  const doc=base("CATÁLOGO DE RUTAS",`${routes.length} registros`,dateStamp(),"landscape");
  const stops=(raw:unknown)=>{try{const parsed=Array.isArray(raw)?raw:JSON.parse(String(raw||"[]"));return (parsed as Info[]).map((stop,i)=>`${value(stop.orden||i+1)}. ${value(stop.ciudad||stop.nombre||stop.ciudad_id)}${stop.tiempo_espera?` (${value(stop.tiempo_espera)} min)`:""}`).join("; ")||"Sin paradas";}catch{return "Sin paradas";}};
  autoTable(doc,{startY:46,margin:{left:10,right:10,top:14,bottom:20},head:[["CÓDIGO","RUTA","ORIGEN","DESTINO","DISTANCIA (KM)","DURACIÓN","ESTADO","PARADAS"]],body:routes.map(route=>[value(route.codigo),value(route.nombre),value(route.origen),value(route.destino),value(route.distancia_km),`${value(route.duracion_minutos)} min`,value(route.estado),stops(route.paradas)]),theme:"grid",headStyles:{fillColor:blue,fontSize:8},styles:{fontSize:8,cellPadding:2.5,overflow:"linebreak"},columnStyles:{7:{cellWidth:65}},showHead:"everyPage"});
  finish(doc,`rutas-${dateStamp()}.pdf`,false);
}

export function exportVehiclesPdf(vehicles: Info[]) {
  const doc=base("CATÁLOGO DE VEHÍCULOS",`${vehicles.length} registros`,dateStamp(),"landscape");
  autoTable(doc,{startY:46,margin:{left:10,right:10,top:14,bottom:20},head:[["CÓDIGO DE FLOTA","PLACA","TIPO","REMOLQUE","VIN","CAPACIDAD (KG)","ESTADO"]],body:vehicles.map(vehicle=>[value(vehicle.codigo_flota),value(vehicle.placa),value(vehicle.tipo),vehicle.tiene_remolque?value(vehicle.placa_remolque):"No",value(vehicle.vin),Number(vehicle.capacidad_kg||0).toLocaleString("es-PE"),value(vehicle.estado)]),theme:"grid",headStyles:{fillColor:blue,fontSize:8},styles:{fontSize:8,cellPadding:3,overflow:"linebreak"},showHead:"everyPage"});
  finish(doc,`vehiculos-${dateStamp()}.pdf`,false);
}

export function exportLoadPdf(load: Info, client?: Info, trips: Info[] = [], vehicle?: Info, driver?: Info) {
  const doc=base("NOTA DE CARGA",load.codigo,load.fecha_recojo||load.created_at);
  let y=section(doc,"REMITENTE / CLIENTE",45);
  y=facts(doc,[["Cliente",client?.nombre||load.cliente_id],["Documento",client?.documento],["Origen",load.procedencia],["Destino",load.destino],["Contacto",client?.telefono],["Correo",client?.correo]],y);
  y=section(doc,"DESCRIPCIÓN DE LA CARGA",y);
  autoTable(doc,{startY:y,head:[["ÍTEM","CÓDIGO","PRODUCTO","VARIEDAD","CANTIDAD","PESO NETO (KG)","PESO BRUTO (KG)" ]],body:[["1",value(load.codigo),value(load.producto),value(load.variedad),`${value(load.cantidad)} ${value(load.unidad)}`,value(load.peso_neto_total_kg||load.peso_neto),value(load.peso_bruto_total_kg||load.peso_bruto)]],theme:"grid",headStyles:{fillColor:blue,fontSize:8},styles:{fontSize:8,cellPadding:3}});
  y=(doc as jsPDF & {lastAutoTable:{finalY:number}}).lastAutoTable.finalY+8;
  y=section(doc,"DETALLES DEL TRANSPORTE",y);
  const stageNames=(load.etapas as Info[]|undefined)?.map(s=>value(s.viaje_codigo)).join(", ")||trips.map(t=>value(t.codigo)).join(", ");
  facts(doc,[["Viaje(s)",stageNames],["Vehículo",vehicle?.placa||"Por asignar"],["Remolque",vehicle?.tiene_remolque?vehicle?.placa_remolque:"No aplica"],["Conductor",driver?.nombre||"Por asignar"],["Estado",load.estado],["Fecha de entrega",load.fecha_entrega]],y);
  finish(doc,`${value(load.codigo)}.pdf`);
}
export function exportTripPdf(trip: Info, route?: Info, loads: Info[] = [], vehicle?: Info, driver?: Info) {
  const doc=base("ORDEN DE VIAJE",trip.codigo,trip.fecha_salida_programada);
  let y=section(doc,"DETALLES DEL TRASLADO",45);
  y=facts(doc,[["Ruta",route?.nombre||trip.ruta_id],["Origen",route?.origen],["Destino",route?.destino],["Llegada estimada",trip.fecha_entrega_estimada],["Vehículo",vehicle?.placa],["Remolque",vehicle?.tiene_remolque?vehicle?.placa_remolque:"No aplica"],["Conductor",driver?.nombre],["Estado",trip.estado]],y);
  y=section(doc,"CARGAS ASIGNADAS",y);
  autoTable(doc,{startY:y,head:[["CÓDIGO","CLIENTE","PRODUCTO","ORIGEN","DESTINO","PESO (KG)","ESTADO"]],body:loads.length?loads.map(l=>[value(l.codigo),value(l.cliente_nombre||l.cliente_id),value(l.producto),value(l.procedencia),value(l.destino),value(l.peso_neto_total_kg||l.peso_neto),value(l.estado)]):[["Sin cargas asignadas","—","—","—","—","—","—"]],theme:"grid",headStyles:{fillColor:blue,fontSize:8},styles:{fontSize:8,cellPadding:3}});
  finish(doc,`${value(trip.codigo)}.pdf`);
}
export function exportRoutePdf(route: Info) {
  const doc=base("FICHA DE RUTA",route.codigo,route.created_at);
  let y=section(doc,"DATOS DE LA RUTA",45);
  y=facts(doc,[["Nombre",route.nombre],["Origen",route.origen],["Destino",route.destino],["Distancia",`${value(route.distancia_km)} km`],["Duración estimada",`${value(route.duracion_minutos)} minutos`],["Tarifa referencial",`${value(route.tarifa_referencial_minor)} céntimos PEN`],["Estado",route.estado],["Notas",route.notas]],y);
  y=section(doc,"PARADAS DEL RECORRIDO",y);
  let stops: Info[]=[];try{stops=Array.isArray(route.paradas)?route.paradas as Info[]:JSON.parse(String(route.paradas||"[]"));}catch{}
  autoTable(doc,{startY:y,head:[["ORDEN","CIUDAD","ESPERA (MIN)"]],body:stops.length?stops.map((s,i)=>[value(s.orden||i+1),value(s.ciudad||s.nombre||s.ciudad_id),value(s.tiempo_espera)]):[["—","Sin paradas intermedias","—"]],theme:"grid",headStyles:{fillColor:blue,fontSize:9},styles:{fontSize:9,cellPadding:3}});
  finish(doc,`${value(route.codigo)}.pdf`);
}
