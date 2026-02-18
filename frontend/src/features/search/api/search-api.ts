"use client";

import { apiRequest } from "@/lib/api/client";

export type SearchScopeMode = "visible" | "filtered" | "explicit";
export type SearchSortField = "created_at" | "updated_at" | "title" | "price" | "sku" | "id";
export type SearchSortDir = "asc" | "desc";

export type ProductSearchRequest = {
  q?: string;
  sku?: string;
  barcode?: string;
  hs_code?: string;
  vendor_code?: string;
  title?: string;
  tags?: string;
  product_type?: string;
  status?: "active" | "draft" | "inactive";
  price_min?: number;
  price_max?: number;
  inventory_total_min?: number;
  inventory_total_max?: number;
  sort_by?: SearchSortField;
  sort_dir?: SearchSortDir;
  cursor?: string;
  limit?: number;
  scope_mode?: SearchScopeMode;
};

export type ProductSearchRow = {
  id: number;
  sku: string | null;
  barcode: string | null;
  title: string | null;
  vendor_code: string | null;
  shopify_product_id: string | null;
  price: number | null;
  compare_at_price: number | null;
  weight_grams: number | null;
  status: string | null;
  created_at: string | null;
  updated_at: string | null;
  inventory_total: number | null;
  protected_columns: string[];
};

export type ProductSearchResponse = {
  data: ProductSearchRow[];
  pagination: {
    limit: number;
    has_next: boolean;
    next_cursor?: string | null;
  };
  scope: {
    scope_mode: SearchScopeMode;
    total_matching: number;
    selection_token: string;
  };
};

function appendIfPresent(params: URLSearchParams, key: string, value: unknown): void {
  if (value === undefined || value === null) return;
  if (typeof value === "string" && value.trim() === "") return;
  params.set(key, String(value));
}

export function buildProductSearchPath(request: ProductSearchRequest): string {
  const params = new URLSearchParams();
  appendIfPresent(params, "q", request.q);
  appendIfPresent(params, "sku", request.sku);
  appendIfPresent(params, "barcode", request.barcode);
  appendIfPresent(params, "hs_code", request.hs_code);
  appendIfPresent(params, "vendor_code", request.vendor_code);
  appendIfPresent(params, "title", request.title);
  appendIfPresent(params, "tags", request.tags);
  appendIfPresent(params, "product_type", request.product_type);
  appendIfPresent(params, "status", request.status);
  appendIfPresent(params, "price_min", request.price_min);
  appendIfPresent(params, "price_max", request.price_max);
  appendIfPresent(params, "inventory_total_min", request.inventory_total_min);
  appendIfPresent(params, "inventory_total_max", request.inventory_total_max);
  appendIfPresent(params, "sort_by", request.sort_by);
  appendIfPresent(params, "sort_dir", request.sort_dir);
  appendIfPresent(params, "cursor", request.cursor);
  appendIfPresent(params, "limit", request.limit);
  appendIfPresent(params, "scope_mode", request.scope_mode);

  const query = params.toString();
  return query ? `/api/v1/products/search?${query}` : "/api/v1/products/search";
}

export async function fetchProductSearch(
  request: ProductSearchRequest,
  signal?: AbortSignal,
): Promise<ProductSearchResponse> {
  return apiRequest<ProductSearchResponse>(buildProductSearchPath(request), { signal });
}
