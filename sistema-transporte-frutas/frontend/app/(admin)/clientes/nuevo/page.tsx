import { Suspense } from "react";
import ClientForm from "@/features/clientes/ClientForm";

export default function Page() {
  return <Suspense><ClientForm /></Suspense>;
}
