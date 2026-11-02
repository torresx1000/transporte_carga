import { Suspense } from "react";
import PaymentsWorkspace from "@/features/pagos/PaymentsWorkspace";

export default function Page() {
  return <Suspense><PaymentsWorkspace newPage /></Suspense>;
}
