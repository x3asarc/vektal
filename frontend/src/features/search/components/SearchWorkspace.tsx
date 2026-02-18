"use client";

import { FormEvent, useEffect, useState } from "react";
import { SearchScopeMode } from "@/features/search/api/search-api";
import { BulkActionBuilder } from "@/features/search/components/BulkActionBuilder";
import { ProductDetailPanel } from "@/features/search/components/ProductDetailPanel";
import { ProductDiffPanel } from "@/features/search/components/ProductDiffPanel";
import { SearchResultGrid } from "@/features/search/components/SearchResultGrid";
import { useSearchWorkspace } from "@/features/search/hooks/useSearchWorkspace";

export function SearchWorkspace() {
  const {
    request,
    rows,
    error,
    isLoading,
    totalMatching,
    scopeMode,
    selectedCount,
    scopeFreeze,
    updateRequest,
    setScopeMode,
    toggleSelected,
    clearSelection,
    persistSelectionAfterFilterChange,
  } = useSearchWorkspace();

  const [q, setQ] = useState(request.q ?? "");
  const [vendorCode, setVendorCode] = useState(request.vendor_code ?? "");
  const [status, setStatus] = useState(request.status ?? "");

  const selectedRows = rows.filter((row) => scopeFreeze.selectedIds.includes(row.id));
  const primarySelected = selectedRows[0] ?? null;

  useEffect(() => {
    setQ(request.q ?? "");
    setVendorCode(request.vendor_code ?? "");
    setStatus(request.status ?? "");
  }, [request.q, request.vendor_code, request.status]);

  function onApplyFilters(event: FormEvent) {
    event.preventDefault();
    updateRequest({
      q,
      vendor_code: vendorCode || undefined,
      status: status ? (status as "active" | "draft" | "inactive") : undefined,
    });
    persistSelectionAfterFilterChange();
  }

  return (
    <div className="page-wrap" data-testid="search-workspace" data-section="search-controls">
      {/* Page header */}
      <div className="page-header">
        <h1 className="page-title">
          <span className="material-symbols-rounded" style={{ marginRight: 8 }}>search</span>
          Catalog Search
        </h1>
        <p className="page-subtitle">Precision product discovery with selection scope control.</p>
      </div>

      {/* Scrollable body */}
      <div className="page-body">
        {/* Filters bar */}
        <form className="search-filters-bar" onSubmit={onApplyFilters} data-section="search-controls">
          <label>
            Query
            <input
              type="text"
              placeholder="SKU, barcode, title, vendor…"
              value={q}
              onChange={(event) => setQ(event.target.value)}
            />
          </label>
          <label>
            Vendor code
            <input
              type="text"
              placeholder="e.g. PENTART"
              value={vendorCode}
              onChange={(event) => setVendorCode(event.target.value)}
            />
          </label>
          <label>
            Status
            <select value={status} onChange={(event) => setStatus(event.target.value)}>
              <option value="">Any</option>
              <option value="active">active</option>
              <option value="draft">draft</option>
              <option value="inactive">inactive</option>
            </select>
          </label>
          <div className="search-filters-actions">
            <button className="btn-primary" type="submit" style={{ fontSize: "0.8rem", padding: "7px 16px" }}>
              <span className="material-symbols-rounded" style={{ fontSize: 15, marginRight: 4 }}>filter_list</span>
              Apply
            </button>
            <button
              className="btn-ghost"
              type="button"
              style={{ fontSize: "0.8rem", padding: "7px 12px" }}
              onClick={() => {
                setQ(""); setVendorCode(""); setStatus("");
                updateRequest({ q: undefined, vendor_code: undefined, status: undefined });
              }}
            >
              Reset
            </button>
          </div>
        </form>

        {/* Scope bar */}
        <div className="search-scope-bar" data-testid="selection-scope-banner">
          <span>
            <span className="material-symbols-rounded" style={{ fontSize: 15, marginRight: 4 }}>frame_inspect</span>
            Scope: <strong>{scopeMode}</strong>
          </span>
          <span>Selected: <strong>{selectedCount}</strong></span>
          <span>Matching: <strong>{totalMatching}</strong></span>
          <label style={{ display: "flex", alignItems: "center", gap: 6 }}>
            Mode:
            <select
              value={scopeMode}
              onChange={(event) => setScopeMode(event.target.value as SearchScopeMode)}
            >
              <option value="visible">visible</option>
              <option value="filtered">filtered</option>
              <option value="explicit">explicit</option>
            </select>
          </label>
          <code data-testid="selection-freeze-token" style={{ fontSize: "0.68rem", color: "var(--muted)" }}>
            {scopeFreeze.selectionToken}
          </code>
          <button className="btn-ghost" type="button" onClick={clearSelection} style={{ fontSize: "0.75rem", padding: "4px 10px", marginLeft: "auto" }}>
            Clear selection
          </button>
        </div>

        {error ? (
          <p style={{ color: "var(--error)", margin: 0 }}>Search error: {error}</p>
        ) : null}
        {isLoading ? <p className="muted" style={{ margin: 0 }}>Loading search results…</p> : null}

        <SearchResultGrid rows={rows} selectedIds={new Set(scopeFreeze.selectedIds)} onToggleSelected={toggleSelected} />
        <ProductDetailPanel product={primarySelected} />
        <ProductDiffPanel
          rows={
            primarySelected
              ? [
                  {
                    field: "title",
                    before: primarySelected.title,
                    after: `${primarySelected.title ?? ""} (staged)`,
                  },
                  {
                    field: "alt_text",
                    before: "-",
                    after: "candidate alt text",
                    altTextState: "candidate",
                  },
                ]
              : []
          }
        />
        <BulkActionBuilder
          selectedRows={selectedRows}
          selection={{
            scopeMode,
            totalMatching,
            selectionToken: scopeFreeze.selectionToken,
            selectedIds: scopeFreeze.selectedIds,
          }}
        />
      </div>
    </div>
  );
}
