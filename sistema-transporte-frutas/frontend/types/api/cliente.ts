import type { components } from "@/types/api/schema";

export type ApiClientRecord = components["schemas"]["ClienteResponse"];
export type ClientPayload = components["schemas"]["ClienteCreate"];
export type ClientUpdatePayload = components["schemas"]["ClienteUpdate"];
export type ClientPage = components["schemas"]["PageResponse_ClienteResponse_"];
