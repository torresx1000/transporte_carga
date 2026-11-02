export type RouteStatus = "Activa" | "Inactiva";
export type TransportRoute = {
  id: string;
  code: string;
  name: string;
  origin: string;
  destination: string;
  stops: string[];
  distance: number;
  duration: string;
  tolls: number;
  referencePrice: number;
  status: RouteStatus;
  lastUsed: string;
  notes: string;
};
