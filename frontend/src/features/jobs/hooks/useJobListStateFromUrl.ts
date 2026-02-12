"use client";

import { useMemo } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

export type JobListUrlState = {
  status: string | null;
  search: string | null;
  page: number;
};

const PAGE_PARAM = "page";
const STATUS_PARAM = "status";
const SEARCH_PARAM = "q";

export function parseJobListState(params: URLSearchParams): JobListUrlState {
  const pageRaw = Number(params.get(PAGE_PARAM) ?? "1");
  const page = Number.isFinite(pageRaw) && pageRaw > 0 ? Math.floor(pageRaw) : 1;
  const status = params.get(STATUS_PARAM);
  const search = params.get(SEARCH_PARAM);
  return {
    status: status && status.length > 0 ? status : null,
    search: search && search.length > 0 ? search : null,
    page,
  };
}

export function buildJobListQuery(state: JobListUrlState): string {
  const next = new URLSearchParams();
  if (state.status) next.set(STATUS_PARAM, state.status);
  if (state.search) next.set(SEARCH_PARAM, state.search);
  if (state.page > 1) next.set(PAGE_PARAM, String(state.page));
  return next.toString();
}

export function resetWorkspaceQuery(): string {
  return "";
}

export function useJobListStateFromUrl() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();

  const state = useMemo(
    () => parseJobListState(new URLSearchParams(params.toString())),
    [params],
  );

  function replaceWith(nextState: JobListUrlState) {
    const query = buildJobListQuery(nextState);
    router.replace(query ? `${pathname}?${query}` : pathname);
  }

  return {
    state,
    setStatus: (status: string | null) => {
      replaceWith({ ...state, status, page: 1 });
    },
    setSearch: (search: string | null) => {
      replaceWith({ ...state, search, page: 1 });
    },
    setPage: (page: number) => {
      replaceWith({ ...state, page: page < 1 ? 1 : Math.floor(page) });
    },
    resetWorkspace: () => {
      const query = resetWorkspaceQuery();
      router.replace(query ? `${pathname}?${query}` : pathname);
    },
  };
}
