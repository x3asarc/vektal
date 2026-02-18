import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BulkActionBuilder } from "@/features/search/components/BulkActionBuilder";

function renderWithQueryClient(ui: React.ReactNode) {
  const queryClient = new QueryClient();
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

afterEach(() => {
  cleanup();
});

describe("BulkActionBuilder", () => {
  it("renders semantic operation options", () => {
    renderWithQueryClient(
      <BulkActionBuilder
        selectedRows={[
          {
            id: 1,
            sku: "SKU-1",
            barcode: "111",
            title: "Product One",
            vendor_code: "PENTART",
            shopify_product_id: "123",
            price: 10,
            compare_at_price: null,
            weight_grams: null,
            status: "active",
            created_at: null,
            updated_at: null,
            inventory_total: null,
            protected_columns: ["id", "shopify_product_id"],
          },
        ]}
        selection={{
          scopeMode: "explicit",
          totalMatching: 1,
          selectionToken: "tok-1234",
          selectedIds: [1],
        }}
      />,
    );

    expect(screen.getByTestId("bulk-action-builder")).toBeInTheDocument();
    expect(screen.getByText("set")).toBeInTheDocument();
    expect(screen.getByText("replace")).toBeInTheDocument();
    expect(screen.getByText("increase")).toBeInTheDocument();
    expect(screen.getByText("conditional_set")).toBeInTheDocument();
  });

  it("shows protected field indicators", () => {
    renderWithQueryClient(
      <BulkActionBuilder
        selectedRows={[]}
        selection={{
          scopeMode: "explicit",
          totalMatching: 0,
          selectionToken: "tok-1234",
          selectedIds: [],
        }}
      />,
    );

    expect(screen.getByTestId("bulk-action-builder")).toBeInTheDocument();
    expect(screen.getByText("id")).toBeInTheDocument();
    expect(screen.getByText("store_id")).toBeInTheDocument();
    expect(screen.getByText("shopify_product_id")).toBeInTheDocument();
    expect(screen.getByText("shopify_variant_id")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Stage action block" })).toBeDisabled();
  });
});
