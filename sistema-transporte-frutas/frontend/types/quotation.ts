export type QuotationStatus = "Borrador" | "Enviada" | "Aprobada" | "Rechazada" | "Vencida";
export type Quotation = {
  id: string;
  code: string;
  client: string;
  contact: string;
  phone: string;
  origin: string;
  destination: string;
  product: string;
  weight: number;
  vehicleType: string;
  amount: number;
  issuedAt: string;
  validUntil: string;
  status: QuotationStatus;
  notes: string;
};
