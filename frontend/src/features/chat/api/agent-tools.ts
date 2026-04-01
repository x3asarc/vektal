import { z } from "zod";
import { apiRequest } from "@/lib/api/client";

/**
 * Zod-based tool manifest for the Vercel AI SDK.
 * These tools allow the AI Agent to interact directly with the backend.
 */
export const agentTools = {
  // --- OPS & DASHBOARD TOOLS ---
  get_catalog_health: {
    description: "Get catalog-wide completeness metrics, SKU health, and field coverage summaries.",
    parameters: z.object({}),
    execute: async () => apiRequest("/api/v1/ops/dashboard/summary"),
  },

  // --- JOB & INGEST TOOLS ---
  list_jobs: {
    description: "List recent background jobs (ingests, enrichments, syncs) and their current status.",
    parameters: z.object({
      limit: z.number().optional().default(10),
      status: z.enum(["queued", "running", "completed", "failed", "cancelled"]).optional(),
    }),
    execute: async ({ limit, status }) => {
      const qs = new URLSearchParams();
      if (limit) qs.append("limit", limit.toString());
      if (status) qs.append("status", status);
      return apiRequest(`/api/v1/jobs?${qs.toString()}`);
    },
  },
  start_ingest_job: {
    description: "Start a new background catalog ingest job for a specific vendor/supplier.",
    parameters: z.object({
      vendor_code: z.string().describe("The code of the vendor to ingest (e.g., 'PENTART')"),
      chunk_size: z.number().optional().default(100),
    }),
    execute: async (body) => apiRequest("/api/v1/jobs", { method: "POST", body }),
  },

  // --- PRODUCT & ENRICHMENT TOOLS ---
  search_products: {
    description: "Search the local isolated catalog for products by SKU, title, or vendor.",
    parameters: z.object({
      query: z.string().describe("Search term"),
      vendor_code: z.string().optional(),
      limit: z.number().optional().default(20),
    }),
    execute: async ({ query, vendor_code, limit }) => {
      const qs = new URLSearchParams({ q: query });
      if (vendor_code) qs.append("vendor", vendor_code);
      if (limit) qs.append("limit", limit.toString());
      return apiRequest(`/api/v1/products/search?${qs.toString()}`);
    },
  },
  start_enrichment: {
    description: "Initiate an AI enrichment run to fix missing attributes or generate SEO data for a set of SKUs.",
    parameters: z.object({
      skus: z.array(z.string()).describe("List of SKUs to enrich"),
      profile: z.enum(["quick", "standard", "deep"]).optional().default("standard"),
    }),
    execute: async (body) => apiRequest("/api/v1/products/enrichment/runs/start", { method: "POST", body }),
  },

  // --- RESOLUTION & GOVERNANCE TOOLS ---
  create_dry_run: {
    description: "Create a dry-run batch to preview changes before they are applied to Shopify.",
    parameters: z.object({
      supplier_code: z.string(),
      rows: z.array(z.record(z.any())).describe("The product data rows to test against rules"),
    }),
    execute: async (body) => apiRequest("/api/v1/resolution/dry-runs", { method: "POST", body }),
  },
  get_resolution_rules: {
    description: "Retrieve active data resolution and mapping rules for the store.",
    parameters: z.object({
      supplier_code: z.string().optional(),
    }),
    execute: async ({ supplier_code }) => {
      const qs = supplier_code ? `?supplier_code=${encodeURIComponent(supplier_code)}` : "";
      return apiRequest(`/api/v1/resolution/rules${qs}`);
    },
  },

  // --- CHAT & BULK TOOLS ---
  apply_bulk_action: {
    description: "Execute an approved bulk action (e.g., update prices or sync inventory) across many SKUs.",
    parameters: z.object({
      action_id: z.number(),
      mode: z.enum(["immediate", "scheduled"]).optional().default("immediate"),
    }),
    execute: async ({ action_id, mode }) => 
      apiRequest(`/api/v1/chat/actions/${action_id}/apply`, { method: "POST", body: { mode } }),
  },
};
