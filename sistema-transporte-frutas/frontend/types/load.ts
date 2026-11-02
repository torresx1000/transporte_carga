export type LoadStatus = "Pendiente de programación" | "Asignada" | "En tránsito" | "Entregada";

export type Load = {
  id: string;
  code: string;
  fruit: string;
  variety: string;
  client: string;
  quantity: number;
  unit: string;
  weight: number;
  status: LoadStatus;
  origin: string;
  destination: string;
  registeredAt: string;
  pickupDate: string;
  deliveryDate: string;
  trip?: string;
  vehicle?: string;
  driver?: string;
  contact: string;
  phone: string;
  notes: string;
  jabasDispatched?: number;
};
