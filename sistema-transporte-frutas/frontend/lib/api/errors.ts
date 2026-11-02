import axios from "axios";
import type { components } from "@/types/api/schema";

type ApiErrorEnvelope = components["schemas"]["ErrorResponse"];

function isErrorEnvelope(value: unknown): value is ApiErrorEnvelope {
  return typeof value === "object" && value !== null &&
    "code" in value && typeof value.code === "string" &&
    "message" in value && typeof value.message === "string";
}

function validationDetails(details: unknown): string | null {
  if (!Array.isArray(details)) return null;
  const fields = details.flatMap((item) => {
    if (typeof item !== "object" || item === null) return [];
    const error = item as { loc?: unknown; msg?: unknown };
    const location = Array.isArray(error.loc) ? error.loc.filter((part) => part !== "body").join(".") : "";
    const message = typeof error.msg === "string" ? error.msg : "Dato inválido";
    return [location ? `${location}: ${message}` : message];
  });
  return fields.length ? fields.join(" · ") : null;
}

export function getApiFieldErrors(error: unknown): Record<string, string> {
  if (!axios.isAxiosError(error)) return {};
  const payload: unknown = error.response?.data;
  if (!isErrorEnvelope(payload)) return {};
  if (payload.code === "CLIENT_DOCUMENT_ARCHIVED" || payload.code === "CLIENT_DOCUMENT_DUPLICATE") {
    return { documento: payload.message };
  }
  const details = payload.details;
  if (!Array.isArray(details)) {
    if (typeof details === "object" && details !== null && "field" in details && typeof details.field === "string") {
      return { [details.field]: payload.message };
    }
    return {};
  }
  return Object.fromEntries(details.flatMap((item) => {
    if (typeof item !== "object" || item === null) return [];
    const detail = item as { loc?: unknown; msg?: unknown };
    const field = Array.isArray(detail.loc) ? detail.loc.at(-1) : undefined;
    if (typeof field !== "string" || typeof detail.msg !== "string") return [];
    return [[field, detail.msg]];
  }));
}

export function getApiError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const status = error.response?.status;
    const payload: unknown = error.response?.data;
    if (status === 401) return "Tu sesión venció. Inicia sesión nuevamente.";
    if (status === 403) return "No tienes permiso para esta acción";
    if (status === 404) return "No se encontró el recurso solicitado.";
    if (status === 422) {
      const envelope = isErrorEnvelope(payload) ? payload : null;
      return validationDetails(envelope?.details ?? (payload as { detail?: unknown } | null)?.detail)
        ?? envelope?.message
        ?? "Revisa los campos e intenta nuevamente.";
    }
    if (status === 500) return "Ocurrió un error interno. Intenta nuevamente más tarde.";
    if (isErrorEnvelope(payload)) return payload.message;
    const detail = (payload as { detail?: unknown } | null)?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) return detail.map((item) => item.msg ?? "Dato inválido").join(". ");
    if (!error.response) return "No se pudo conectar con el servidor. Revisa que el backend esté activo.";
    return "Ocurrió un error al procesar la solicitud.";
  }
  return error instanceof Error ? error.message : "Ocurrió un error inesperado.";
}
