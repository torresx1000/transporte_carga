"use client";

import { useResourceCreate, useResourceDelete, useResourceList, useResourceUpdate } from "@/hooks/useResources";
import type { ResourceName } from "@/services/resource.service";

const resource: ResourceName = "vehiculos";
export const useVehiculosList = (filters: { page?: number; page_size?: number; q?: string; estado?: string } = {}) => useResourceList(resource, filters);
export const useCreateVehiculos = () => useResourceCreate(resource);
export const useUpdateVehiculos = () => useResourceUpdate(resource);
export const useDeleteVehiculos = () => useResourceDelete(resource);

