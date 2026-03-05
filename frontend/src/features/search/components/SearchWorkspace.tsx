"use client";

import { FormEvent, useEffect, useState } from "react";
import { OperationalErrorCard } from "@/components/OperationalErrorCard";
import { SearchScopeMode } from "@/features/search/api/search-api";
import { BulkActionBuilder } from "@/features/search/components/BulkActionBuilder";
import { ProductDetailPanel } from "@/features/search/components/ProductDetailPanel";
import { ProductDiffPanel } from "@/features/search/components/ProductDiffPanel";
import { SearchResultGrid } from "@/features/search/components/SearchResultGrid";
import { useSearchWorkspace } from "@/features/search/hooks/useSearchWorkspace";
import { stableDiagnosticId } from "@/lib/diagnostics";

type SearchPreset = {
  id: string;
  name: string;
  q: string;
  vendorCode: string;
  status: string;
};

const SEARCH_PRESETS_KEY = "search.presets.v1";

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
  const [presets, setPresets] = useState<SearchPreset[]>([]);
  const [activePresetId, setActivePresetId] = useState<string>("");

  const selectedRows = rows.filter((row) => scopeFreeze.selectedIds.includes(row.id));
  const primarySelected = selectedRows[0] ?? null;

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(SEARCH_PRESETS_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw) as SearchPreset[];
      if (Array.isArray(parsed)) {
        setPresets(parsed.slice(0, 20));
      }
    } catch {
      // Ignore preset loading failures.
    }
  }, []);

  useEffect(() => {
    setQ(request.q ?? "");
    setVendorCode(request.vendor_code ?? "");
    setStatus(request.status ?? "");
  }, [request.q, request.vendor_code, request.status]);

  function persistPresets(next: SearchPreset[]) {
    setPresets(next);
    try {
      window.localStorage.setItem(SEARCH_PRESETS_KEY, JSON.stringify(next));
    } catch {
      // Ignore storage write failures.
    }
  }

  function saveCurrentPreset() {
    const generated = [vendorCode || "any-vendor", status || "any-status", q || "query"]
      .join(" / ")
      .slice(0, 64);
    const preset: SearchPreset = {
      id: `preset-${Date.now()}`,
      name: generated,
      q,
      vendorCode,
      status,
    };
    const next = [preset, ...presets].slice(0, 20);
    persistPresets(next);
    setActivePresetId(preset.id);
  }

  function applyPresetById(presetId: string) {
    const preset = presets.find((item) => item.id === presetId);
    if (!preset) return;
    setActivePresetId(presetId);
    setQ(preset.q);
    setVendorCode(preset.vendorCode);
    setStatus(preset.status);
    updateRequest({
      q: preset.q || undefined,
      vendor_code: preset.vendorCode || undefined,
      status: preset.status ? (preset.status as "active" | "draft" | "inactive") : undefined,
    });
    persistSelectionAfterFilterChange();
  }

  function deleteActivePreset() {
    if (!activePresetId) return;
    const next = presets.filter((item) => item.id !== activePresetId);
    persistPresets(next);
    setActivePresetId("");
  }

  function onApplyFilters(event: FormEvent) {
    event.preventDefault();
    updateRequest({
      q,
      vendor_code: vendorCode || undefined,
      status: status ? (status as "active" | "draft" | "inactive") : undefined,
    });
    persistSelectionAfterFilterChange();
  }

  function retrySearchRequest() {
    updateRequest({ ...request });
  }

  return (
    <div className="page-wrap" data-testid="search-workspace" data-section="search-controls">
      <div className="page-header">
        <h1 className="page-title">
          <span className="material-symbols-rounded title-icon">search</span>
          Catalog Search
        </h1>
        <p className="page-subtitle">Precision product discovery with selection scope control.</p>
      </div>

      <div className="page-body">
        <section className="panel search-presets-row">
          <h2 className="forensic-card-title forensic-zero-top">Saved Search Presets</h2>
          <div className="search-presets-controls">
            <select
              value={activePresetId}
              onChange={(event) => applyPresetById(event.target.value)}
              aria-label="saved search presets"
            >
              <option value="">Select preset</option>
              {presets.map((preset) => (
                <option key={preset.id} value={preset.id}>
                  {preset.name}
                </option>
              ))}
            </select>
            <button className="btn-ghost" type="button" onClick={saveCurrentPreset}>
              Save current
            </button>
            <button className="btn-ghost" type="button" onClick={deleteActivePreset} disabled={!activePresetId}>
              Delete preset
            </button>
          </div>
        </section>

        <form className="search-filters-bar" onSubmit={onApplyFilters} data-section="search-controls">
          <label className="forensic-field">
            <span className="forensic-field-label">Query</span>
            <input
              type="text"
              placeholder="SKU, barcode, title, vendor..."
              value={q}
              onChange={(event) => setQ(event.target.value)}
            />
          </label>
          <label className="forensic-field">
            <span className="forensic-field-label">Vendor code</span>
            <input
              type="text"
              placeholder="e.g. PENTART"
              value={vendorCode}
              onChange={(event) => setVendorCode(event.target.value)}
            />
          </label>
          <label className="forensic-field">
            <span className="forensic-field-label">Status</span>
            <select value={status} onChange={(event) => setStatus(event.target.value)}>
              <option value="">Any</option>
              <option value="active">active</option>
              <option value="draft">draft</option>
              <option value="inactive">inactive</option>
            </select>
          </label>
          <div className="search-filters-actions">
            <button className="btn-primary" type="submit">
              <span className="material-symbols-rounded icon-sm">filter_list</span>
              Apply
            </button>
            <button
              className="btn-ghost"
              type="button"
              onClick={() => {
                setQ("");
                setVendorCode("");
                setStatus("");
                updateRequest({ q: undefined, vendor_code: undefined, status: undefined });
              }}
            >
              Reset
            </button>
          </div>
        </form>

        <div className="search-scope-bar" data-testid="selection-scope-banner">
          <span className="forensic-inline-note">
            <span className="material-symbols-rounded icon-sm">frame_inspect</span>
            Scope: <strong>{scopeMode}</strong>
          </span>
          <span>Selected: <strong>{selectedCount}</strong></span>
          <span>Matching: <strong>{totalMatching}</strong></span>
          <label className="search-scope-label">
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
          <code data-testid="selection-freeze-token" className="search-token">
            {scopeFreeze.selectionToken}
          </code>
          <button className="btn-ghost search-clear-btn" type="button" onClick={clearSelection}>
            Clear selection
          </button>
        </div>

        {error ? (
          <OperationalErrorCard
            title="Search request failed"
            detail={error}
            diagnosticId={stableDiagnosticId(error)}
            retryLabel="Retry search"
            onRetry={retrySearchRequest}
          />
        ) : null}
        {isLoading ? <p className="muted search-loading">Loading search results...</p> : null}

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
