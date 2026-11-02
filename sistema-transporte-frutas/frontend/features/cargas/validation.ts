import axios from "axios";

export type FieldErrors = Record<string, string>;
export function validationMessage(type: string, context: Record<string, unknown> = {}): string {
  if (type === "missing") return "Este campo es obligatorio.";
  if (["decimal_parsing", "decimal_type", "float_parsing", "int_parsing", "finite_number", "badInput"].includes(type)) return "Ingresa un número válido.";
  if (type === "int_from_float") return "Ingresa un número entero.";
  if (type === "enum" || type === "literal_error") return "Selecciona una opción válida.";
  if (type === "greater_than") return `Ingresa un valor mayor que ${context.gt}.`;
  if (type === "greater_than_equal") return `El valor mínimo es ${context.ge}.`;
  if (type === "less_than_equal") return `El valor máximo es ${context.le}.`;
  if (type === "string_too_long") return `Usa como máximo ${context.max_length} caracteres.`;
  if (type === "string_too_short") return `Ingresa al menos ${context.min_length} caracteres.`;
  if (type.startsWith("date")) return "Ingresa una fecha válida.";
  if (type.startsWith("decimal_")) return "Revisa la cantidad de dígitos y decimales.";
  return "Revisa el valor ingresado.";
}

export function loadFieldErrors(error: unknown): FieldErrors {
  if (!axios.isAxiosError(error)) return {};
  const payload = error.response?.data as { details?: unknown; detail?: unknown; message?: string } | undefined;
  const details = payload?.details ?? payload?.detail;
  if (details && !Array.isArray(details) && typeof details === "object" && "field" in details && typeof details.field === "string") return { [details.field]: payload?.message || "Revisa este campo." };
  if (!Array.isArray(details)) return {};
  const result: FieldErrors = {};
  const aliases: Record<string, string> = { fruta: "producto", unidad_peso: "unidad", peso_neto: "peso_neto_total_kg", peso_bruto: "peso_bruto_total_kg", notas: "observaciones" };
  for (const detail of details) {
    if (!detail || !Array.isArray(detail.loc) || detail.type === "extra_forbidden") continue;
    const field = detail.loc.filter((part: unknown) => part !== "body" && part !== "data")[0];
    if (typeof field === "string") result[aliases[field] || field] = validationMessage(String(detail.type), detail.ctx);
  }
  return result;
}

export function validateLoadForm(form: HTMLFormElement): FieldErrors {
  const errors: FieldErrors = {};
  for (const element of Array.from(form.elements)) {
    if (!(element instanceof HTMLInputElement || element instanceof HTMLSelectElement || element instanceof HTMLTextAreaElement) || !element.name || element.disabled) continue;
    const validity = element.validity;
    if (validity.valueMissing || (element.required && !element.value.trim())) errors[element.name] = "Este campo es obligatorio.";
    else if (validity.badInput) errors[element.name] = "Ingresa un número válido.";
    else if (validity.rangeUnderflow) errors[element.name] = `El valor mínimo es ${element.getAttribute("min")}.`;
    else if (validity.rangeOverflow) errors[element.name] = `El valor máximo es ${element.getAttribute("max")}.`;
    else if (validity.stepMismatch) errors[element.name] = ["cantidad", "jabas_despachadas"].includes(element.name) ? "Ingresa un número entero." : "Usa como máximo tres decimales.";
    else if (!validity.valid) errors[element.name] = "Revisa el valor ingresado.";
  }
  const data = new FormData(form);
  if (data.get("origen_id") && data.get("origen_id") === data.get("destino_id")) errors.destino_id = "El destino debe ser diferente del origen.";
  if (data.get("fecha_recojo") && data.get("fecha_entrega") && String(data.get("fecha_entrega")) < String(data.get("fecha_recojo"))) errors.fecha_entrega = "La entrega no puede ser anterior al recojo.";
  const net = data.get("peso_neto_total_kg"), gross = data.get("peso_bruto_total_kg");
  if (net && gross && Number(gross) < Number(net)) errors.peso_bruto_total_kg = "El peso bruto no puede ser menor al peso neto.";
  return errors;
}
