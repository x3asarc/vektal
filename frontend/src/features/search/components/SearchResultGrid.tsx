"use client";

import { useMemo, useState } from "react";
import { ProductSearchRow } from "@/features/search/api/search-api";

export type SearchColumnKey =
  | "id"
  | "sku"
  | "title"
  | "vendor_code"
  | "price"
  | "status"
  | "shopify_product_id";

export type SearchColumn = {
  key: SearchColumnKey;
  label: string;
  protected: boolean;
};

export const SEARCH_COLUMNS: SearchColumn[] = [
  { key: "id", label: "ID", protected: true },
  { key: "sku", label: "SKU", protected: false },
  { key: "title", label: "Title", protected: false },
  { key: "vendor_code", label: "Vendor", protected: false },
  { key: "price", label: "Price", protected: false },
  { key: "status", label: "Status", protected: false },
  { key: "shopify_product_id", label: "Shopify Product ID", protected: true },
];

const DEFAULT_VISIBLE_COLUMNS: SearchColumnKey[] = [
  "id",
  "sku",
  "title",
  "vendor_code",
  "price",
  "status",
];

type SearchResultGridProps = {
  rows: ProductSearchRow[];
  selectedIds: Set<number>;
  onToggleSelected: (id: number) => void;
};

function renderCellValue(row: ProductSearchRow, key: SearchColumnKey): string {
  const value = row[key];
  if (value === null || value === undefined || value === "") return "-";
  if (key === "price" && typeof value === "number") return `$${value.toFixed(2)}`;
  return String(value);
}

export function SearchResultGrid({
  rows,
  selectedIds,
  onToggleSelected,
}: SearchResultGridProps) {
  const [visibleColumns, setVisibleColumns] = useState<Set<SearchColumnKey>>(
    new Set(DEFAULT_VISIBLE_COLUMNS),
  );

  const columns = useMemo(
    () => SEARCH_COLUMNS.filter((column) => visibleColumns.has(column.key)),
    [visibleColumns],
  );

  return (
    <section className="panel" data-testid="search-result-grid">
      <h2 className="forensic-card-title">Results</h2>
      <p className="forensic-card-copy">Columns can be toggled per session.</p>
      <div className="forensic-chip-row" style={{ marginBottom: 12 }}>
        {SEARCH_COLUMNS.map((column) => (
          <label key={column.key} className="search-column-toggle">
            <input
              type="checkbox"
              checked={visibleColumns.has(column.key)}
              onChange={(event) => {
                setVisibleColumns((prev) => {
                  const next = new Set(prev);
                  if (event.target.checked) {
                    next.add(column.key);
                  } else {
                    next.delete(column.key);
                  }
                  return next;
                });
              }}
            />
            <span>{column.label}</span>
            {column.protected ? (
              <small data-protected-column="true" className="search-column-lock">
                Protected
              </small>
            ) : null}
          </label>
        ))}
      </div>
      <div className="forensic-table-wrap">
        <table className="forensic-table">
          <thead>
            <tr>
              <th>Select</th>
              {columns.map((column) => (
                <th
                  key={column.key}
                  data-column-key={column.key}
                  data-editable={column.protected ? "false" : "true"}
                >
                  {column.label}
                  {column.protected ? (
                    <span style={{ color: "var(--brand-warning)", marginLeft: 6 }}>(locked)</span>
                  ) : null}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={columns.length + 1}>
                  No products found.
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr key={row.id}>
                  <td>
                    <input
                      aria-label={`Select product ${row.id}`}
                      type="checkbox"
                      checked={selectedIds.has(row.id)}
                      onChange={() => onToggleSelected(row.id)}
                    />
                  </td>
                  {columns.map((column) => (
                    <td key={`${row.id}-${column.key}`}>
                      {renderCellValue(row, column.key)}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
