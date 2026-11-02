export type DriverStatus = "Disponible" | "En viaje" | "Descanso" | "Inactivo";

export type Driver = {
  id: string;
  code: string;
  name: string;
  document: string;
  phone: string;
  email: string;
  location: string;
  licenseNumber: string;
  licenseCategory: string;
  licenseUntil: string;
  medicalUntil: string;
  status: DriverStatus;
  vehicle: string;
  experience: number;
  hiredAt: string;
  emergencyContact: string;
};
