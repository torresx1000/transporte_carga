"use client";

import { useResourceCreate, useResourceDelete, useResourceList, useResourceUpdate } from "@/hooks/useResources";
import type { ResourceName } from "@/services/resource.service";

const resource: ResourceName = "cotizaciones";
export const useCotizacionesList = (filters: { page?: number; page_size?: number; q?: string; estado?: string } = {}) => useResourceList(resource, filters);
export const useCreateCotizaciones = () => useResourceCreate(resource);
export const useUpdateCotizaciones = () => useResourceUpdate(resource);
export const useDeleteCotizaciones = () => useResourceDelete(resource);

