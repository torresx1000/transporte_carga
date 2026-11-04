"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { getApiError } from "@/lib/api/errors";
import { useResourceList } from "@/hooks/useResources";
import type { Load } from "@/features/transporte/data";

type LoadPayment = {
  id: string;
  carga_id?: string;
  sentido?: string;
  estado?: string;
  monto_centimos?: number;
  monto_acordado_centimos?: number;
  monto_pagado_centimos?: number;
  saldo_centimos?: number;
  abonos?: PaymentTransaction[] | string;
  [key: string]: unknown;
};
type PaymentTransaction = { monto_centimos: number; fecha: string; metodo: string; comprobante?: string };

const money = (cents: number) =>
  `S/ ${(cents / 100).toLocaleString("es-PE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const today = () => new Date().toLocaleDateString("en-CA", { timeZone: "America/Lima" });

export default function LoadPaymentAction({ load }: { load: Load }) {
  const cache = useQueryClient();
  const history = useResourceList("pagos", { page: 1, page_size: 100 });
  const client = useQuery({
    queryKey: ["clientes", "detail", load.cliente_id],
    queryFn: async () => (await api.get<{ nombre?: string; name?: string }>(`/clientes/${load.cliente_id}`)).data,
    enabled: Boolean(load.cliente_id),
  });
  const [open, setOpen] = useState(false);
  const [amount, setAmount] = useState("");
  const [method, setMethod] = useState("Transferencia");
  const [date, setDate] = useState(today);
  const [receipt, setReceipt] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const payment = ((history.data?.items || []) as LoadPayment[])
    .filter((item) => item.carga_id === load.id && item.sentido !== "pago_transportista" && item.estado !== "anulado")
    .sort((left, right) => String(right.created_at || "").localeCompare(String(left.created_at || "")))[0];
  const agreed = Number(payment?.monto_acordado_centimos ?? payment?.monto_centimos ?? load.monto_cobrar_centimos ?? 0);
  const paid = payment
    ? Number(payment.monto_pagado_centimos ?? (payment.estado === "pagado" ? agreed : payment.saldo_centimos != null ? agreed - Number(payment.saldo_centimos) : 0))
    : 0;
  const balance = Math.max(0, agreed - paid);
  const settled = Boolean(payment && (payment.estado === "pagado" || (agreed > 0 && balance === 0)));

  function startPayment() {
    setAmount(((balance || agreed) / 100).toFixed(2));
    setDate(today());
    setError("");
    setOpen(true);
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const cents = Math.round(Number(amount) * 100);
    if (!Number.isFinite(cents) || cents <= 0) {
      setError("Ingresa un monto mayor que cero.");
      return;
    }
    if (agreed > 0 && cents > balance) {
      setError(`El cobro no puede superar el saldo pendiente de ${money(balance)}.`);
      return;
    }

    const total = agreed || cents;
    const nextPaid = paid + cents;
    const nextBalance = Math.max(0, total - nextPaid);
    const nextStatus = nextBalance === 0 ? "pagado" : nextPaid > 0 ? "parcial" : "pendiente";
    const transaction = { monto_centimos: cents, fecha: date, metodo: method, comprobante: receipt.trim() };
    let previousTransactions: PaymentTransaction[] = [];
    try {
      if (Array.isArray(payment?.abonos)) {
        previousTransactions = payment.abonos;
      } else if (typeof payment?.abonos === "string" && payment.abonos) {
        const parsed: unknown = JSON.parse(payment.abonos);
        if (!Array.isArray(parsed)) throw new Error("No se pudo leer el historial de abonos de esta carga.");
        previousTransactions = parsed.filter((item): item is PaymentTransaction =>
          Boolean(item) &&
          typeof item === "object" &&
          "monto_centimos" in item &&
          typeof item.monto_centimos === "number" &&
          "fecha" in item &&
          typeof item.fecha === "string" &&
          "metodo" in item &&
          typeof item.metodo === "string",
        );
        if (previousTransactions.length !== parsed.length) {
          throw new Error("El historial de abonos de esta carga tiene un formato no válido.");
        }
      }
    } catch (cause) {
      setError(getApiError(cause));
      return;
    }
    const data = {
      viaje_id: payment?.viaje_id || load.etapas?.[0]?.viaje_id || load.viaje_id || null,
      carga_id: load.id,
      cliente_id: load.cliente_id,
      tipo_servicio: "carga",
      sentido: "cobro_cliente",
      beneficiario: client.data?.nombre || client.data?.name || "Cliente",
      concepto: `${load.producto} · ${load.codigo}`,
      momento_pago: "otro",
      monto_centimos: total,
      monto_acordado_centimos: total,
      monto_pagado_centimos: nextPaid,
      saldo_centimos: nextBalance,
      abonos: [...previousTransactions, transaction],
      fecha_pago: date,
      metodo: method,
      comprobante: receipt.trim(),
      estado: nextStatus,
    };

    setBusy(true);
    setError("");
    try {
      if (payment) {
        await api.patch(`/pagos/${payment.id}`, { data });
      } else {
        await api.post("/pagos", { data });
      }
      await Promise.all([
        cache.invalidateQueries({ queryKey: ["pagos"] }),
        cache.invalidateQueries({ queryKey: ["cargas"] }),
      ]);
      setOpen(false);
    } catch (cause) {
      setError(getApiError(cause));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="fixed bottom-5 right-5 z-40 flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-3 shadow-lg">
        {settled ? (
          <span className="rounded-lg bg-emerald-50 px-4 py-2 text-sm font-semibold text-emerald-800">
            Pago realizado · {money(agreed)}
          </span>
        ) : (
          <button
            type="button"
            disabled={history.isLoading || history.isError}
            onClick={startPayment}
            className="rounded-lg bg-[#2563EB] px-4 py-2 text-sm font-semibold text-white hover:bg-[#1D4ED8] disabled:opacity-50"
          >
            {history.isLoading ? "Cargando pago…" : payment ? "Completar pago" : "Pagar ahora"}
          </button>
        )}
        {history.isError && <span role="alert" className="text-xs text-red-700">{getApiError(history.error)}</span>}
      </div>
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <form onSubmit={submit} className="w-full max-w-lg space-y-4 rounded-xl bg-white p-6 shadow-xl">
            <div>
              <h2 className="text-lg font-semibold">Cobrar {load.producto}</h2>
              <p className="mt-1 text-sm text-slate-600">{load.codigo} · Saldo pendiente: {money(balance || agreed)}</p>
            </div>
            <label className="block text-sm">Monto recibido (S/)
              <input autoFocus required type="number" min="0.01" step="0.01" value={amount} onChange={(event) => setAmount(event.target.value)} className="mt-1 w-full rounded-lg border px-3 py-2" />
            </label>
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="block text-sm">Método de pago
                <select value={method} onChange={(event) => setMethod(event.target.value)} className="mt-1 w-full rounded-lg border bg-white px-3 py-2">
                  {["Transferencia", "Efectivo", "Yape", "Plin", "Tarjeta", "Otro"].map((item) => <option key={item}>{item}</option>)}
                </select>
              </label>
              <label className="block text-sm">Fecha del pago
                <input required type="date" value={date} onChange={(event) => setDate(event.target.value)} className="mt-1 w-full rounded-lg border px-3 py-2" />
              </label>
            </div>
            <label className="block text-sm">Comprobante (opcional)
              <input value={receipt} onChange={(event) => setReceipt(event.target.value)} className="mt-1 w-full rounded-lg border px-3 py-2" />
            </label>
            {error && <p role="alert" className="rounded bg-red-50 p-3 text-sm text-red-700">{error}</p>}
            <div className="flex justify-end gap-3">
              <button type="button" disabled={busy} onClick={() => setOpen(false)} className="rounded-lg border px-4 py-2 text-sm">Cancelar</button>
              <button disabled={busy} className="rounded-lg bg-[#2563EB] px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">
                {busy ? "Registrando…" : "Confirmar cobro"}
              </button>
            </div>
          </form>
        </div>
      )}
    </>
  );
}
