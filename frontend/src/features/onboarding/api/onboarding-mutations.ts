"use client";

import { useMutation } from "@tanstack/react-query";
import { apiRequest } from "@/lib/api/client";
import { usePendingStore } from "@/shell/state/pending-store";

const ACK_FIRST_PREFIXES = [
  "/api/v1/jobs",
  "/api/v1/billing",
  "/api/v1/oauth",
  "/api/v1/auth",
];

export function isAckFirstOnlyEndpoint(path: string): boolean {
  return ACK_FIRST_PREFIXES.some((prefix) => path.startsWith(prefix));
}

type ConnectShopifyPayload = {
  shopDomain: string;
};

type StartImportPayload = {
  ingestPath: "sync_store" | "upload_csv";
  includeAll: boolean;
};

export function buildShopifyOauthPath(shopDomain: string): string {
  const normalized = shopDomain
    .trim()
    .replace(/^https?:\/\//i, "")
    .replace(/\/.*$/, "");

  return `/api/v1/oauth/shopify?shop=${encodeURIComponent(normalized)}`;
}

export function useConnectShopifyMutation() {
  const begin = usePendingStore((state) => state.begin);
  const end = usePendingStore((state) => state.end);

  return useMutation({
    mutationFn: async (payload: ConnectShopifyPayload) => {
      return apiRequest<{ auth_url?: string; state?: string }>(
        buildShopifyOauthPath(payload.shopDomain),
        {
          method: "GET",
          headers: {
            Accept: "application/json",
          },
        },
      );
    },
    onMutate: () => {
      begin();
    },
    onSettled: () => {
      end();
    },
  });
}

export function useStartImportMutation() {
  const begin = usePendingStore((state) => state.begin);
  const end = usePendingStore((state) => state.end);

  return useMutation({
    mutationFn: async (payload: StartImportPayload) => {
      return apiRequest<{ job_id: number | string; status: string }, StartImportPayload>(
        "/api/v1/jobs",
        {
          method: "POST",
          body: payload,
        },
      );
    },
    onMutate: () => {
      begin();
    },
    onSettled: () => {
      end();
    },
  });
}
