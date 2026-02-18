import { Scope } from "@/shared/contracts";

function withScope<T extends readonly unknown[]>(
  resource: string,
  scope: Scope,
  rest: T,
) {
  return [resource, scope, ...rest] as const;
}

export const authKeys = {
  me: (scope: Scope) => withScope("auth", scope, ["me"] as const),
  accountStatus: (scope: Scope) =>
    withScope("auth", scope, ["account-status"] as const),
};

export const jobsKeys = {
  root: (scope: Scope) => withScope("jobs", scope, [] as const),
  list: (scope: Scope, params: { status?: string; page?: number }) =>
    withScope("jobs", scope, ["list", params] as const),
  detail: (scope: Scope, jobId: string) =>
    withScope("jobs", scope, ["detail", { jobId }] as const),
  status: (scope: Scope, jobId: string) =>
    withScope("jobs", scope, ["status", { jobId }] as const),
};

export const billingKeys = {
  plans: (scope: Scope) => withScope("billing", scope, ["plans"] as const),
  subscription: (scope: Scope) =>
    withScope("billing", scope, ["subscription"] as const),
};

export const resolutionKeys = {
  root: (scope: Scope) => withScope("resolution", scope, [] as const),
  dryRun: (scope: Scope, batchId: number) =>
    withScope("resolution", scope, ["dry-run", { batchId }] as const),
  lineage: (scope: Scope, batchId: number) =>
    withScope("resolution", scope, ["lineage", { batchId }] as const),
  activity: (scope: Scope) =>
    withScope("resolution", scope, ["activity"] as const),
  rules: (scope: Scope, supplierCode?: string) =>
    withScope("resolution", scope, ["rules", { supplierCode: supplierCode ?? "*" }] as const),
  suggestions: (scope: Scope) =>
    withScope("resolution", scope, ["suggestions"] as const),
};

export function hasScopedKeyShape(key: readonly unknown[]): boolean {
  if (key.length < 2) return false;
  if (typeof key[0] !== "string") return false;
  const scope = key[1];
  if (typeof scope !== "object" || scope === null) return false;
  return "storeId" in scope;
}
