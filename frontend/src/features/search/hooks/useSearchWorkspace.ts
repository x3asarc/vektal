"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { ApiClientError } from "@/lib/api/client";
import {
  fetchProductSearch,
  ProductSearchRequest,
  ProductSearchResponse,
  SearchScopeMode,
} from "@/features/search/api/search-api";

export const DEFAULT_SEARCH_REQUEST: ProductSearchRequest = {
  limit: 25,
  sort_by: "created_at",
  sort_dir: "desc",
  scope_mode: "filtered",
};

export type SelectionFreeze = {
  scopeMode: SearchScopeMode;
  totalMatching: number;
  selectedIds: number[];
  selectionToken: string;
};

export function normalizeSelectedIds(ids: Iterable<number>): number[] {
  return [...new Set(ids)].sort((a, b) => a - b);
}

export function createSelectionFreeze(input: {
  scopeMode: SearchScopeMode;
  totalMatching: number;
  selectedIds: Iterable<number>;
}): SelectionFreeze {
  const normalizedIds = normalizeSelectedIds(input.selectedIds);
  const selectionToken = `${input.scopeMode}:${input.totalMatching}:${normalizedIds.join(",")}`;
  return {
    scopeMode: input.scopeMode,
    totalMatching: input.totalMatching,
    selectedIds: normalizedIds,
    selectionToken,
  };
}

export function preserveSelectionAcrossFilterChange(selectedIds: Iterable<number>): number[] {
  // Filtering must not silently clear a user's explicit selection set.
  return normalizeSelectedIds(selectedIds);
}

export function useSearchWorkspace() {
  const [request, setRequest] = useState<ProductSearchRequest>(DEFAULT_SEARCH_REQUEST);
  const [response, setResponse] = useState<ProductSearchResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());

  useEffect(() => {
    const controller = new AbortController();
    setIsLoading(true);
    setError(null);

    void fetchProductSearch(request, controller.signal)
      .then((payload) => {
        setResponse(payload);
      })
      .catch((reason: unknown) => {
        if (reason instanceof ApiClientError) {
          setError(reason.normalized.detail);
        } else if (reason instanceof Error && reason.name !== "AbortError") {
          setError(reason.message);
        } else if (!(reason instanceof Error)) {
          setError("Unable to load product search results.");
        }
      })
      .finally(() => {
        setIsLoading(false);
      });

    return () => {
      controller.abort();
    };
  }, [request]);

  const rows = response?.data ?? [];
  const totalMatching = response?.scope.total_matching ?? 0;
  const scopeMode = (request.scope_mode ?? "filtered") as SearchScopeMode;
  const selectedCount = selectedIds.size;
  const selectedIdList = useMemo(() => normalizeSelectedIds(selectedIds), [selectedIds]);

  const scopeFreeze = useMemo(
    () =>
      createSelectionFreeze({
        scopeMode,
        totalMatching,
        selectedIds,
      }),
    [scopeMode, totalMatching, selectedIds],
  );

  const updateRequest = useCallback((next: Partial<ProductSearchRequest>) => {
    setRequest((prev) => ({
      ...prev,
      ...next,
      cursor: undefined,
    }));
  }, []);

  const setScopeMode = useCallback((mode: SearchScopeMode) => {
    setRequest((prev) => ({ ...prev, scope_mode: mode, cursor: undefined }));
  }, []);

  const toggleSelected = useCallback((id: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
    setScopeMode("explicit");
  }, [setScopeMode]);

  const clearSelection = useCallback(() => {
    setSelectedIds(new Set());
  }, []);

  const persistSelectionAfterFilterChange = useCallback(() => {
    setSelectedIds((prev) => new Set(preserveSelectionAcrossFilterChange(prev)));
  }, []);

  return {
    request,
    rows,
    isLoading,
    error,
    response,
    totalMatching,
    scopeMode,
    selectedIds,
    selectedIdList,
    selectedCount,
    scopeFreeze,
    updateRequest,
    setScopeMode,
    toggleSelected,
    clearSelection,
    persistSelectionAfterFilterChange,
  };
}
