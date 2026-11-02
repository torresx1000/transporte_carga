export type ReturnLine = { owner: string; quantity: number };
export type CrateReturn = {
  id: string;
  code: string;
  date: string;
  loadId: string;
  loadCode: string;
  loadClient: string;
  deliveredBy: string;
  packagesOf3: number;
  packagesOf2: number;
  looseCrates: number;
  totalReceived: number;
  lines: ReturnLine[];
  observations: string;
};
