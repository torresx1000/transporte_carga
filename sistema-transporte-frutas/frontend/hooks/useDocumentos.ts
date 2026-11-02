"use client";

import { useResourceCreate, useResourceDelete, useResourceList, useResourceUpdate } from "@/hooks/useResources";
import type { ResourceName } from "@/services/resource.service";

const resource: ResourceName = "documentos";
export const useDocumentosList = (filters: { page?: number; page_size?: number; q?: string; estado?: string } = {}) => useResourceList(resource, filters);
export const useCreateDocumentos = () => useResourceCreate(resource);
export const useUpdateDocumentos = () => useResourceUpdate(resource);
export const useDeleteDocumentos = () => useResourceDelete(resource);

