import type { components } from "@/types/api/schema";

/** API record plus a display alias retained by existing cross-module selectors. */
export type Client = components["schemas"]["ClienteResponse"] & { name: string };
export type ClientStatus = Client["estado"];
export type ClientKind = NonNullable<Client["tipo"]>;
