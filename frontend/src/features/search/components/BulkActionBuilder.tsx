"use client";

import { FormEvent, useMemo, useState } from "react";
import { ProductSearchRow } from "@/features/search/api/search-api";
import { ApprovalBlockCard } from "@/features/search/components/ApprovalBlockCard";
import { useBulkStaging } from "@/features/search/hooks/useBulkStaging";

const OPERATIONS = [
  "set",
  "replace",
  "add",
  "remove",
  "clear",
  "increase",
  "decrease",
  "conditional_set",
] as const;

const MUTABLE_FIELDS = [
  "title",
  "description",
  "price",
  "sku",
  "barcode",
  "image_url",
  "product_type",
  "tags",
  "alt_text",
] as const;

const LOCKED_FIELDS = ["id", "store_id", "shopify_product_id", "shopify_variant_id"] as const;

type BulkActionBuilderProps = {
  selectedRows: ProductSearchRow[];
  selection: {
    scopeMode: "visible" | "filtered" | "explicit";
    totalMatching: number;
    selectionToken: string;
    selectedIds: number[];
  };
};

export function BulkActionBuilder({ selectedRows, selection }: BulkActionBuilderProps) {
  const mutation = useBulkStaging();
  const [operation, setOperation] = useState<(typeof OPERATIONS)[number]>("set");
  const [fieldName, setFieldName] = useState<(typeof MUTABLE_FIELDS)[number]>("title");
  const [value, setValue] = useState("Updated from precision workspace");
  const [supplierCode, setSupplierCode] = useState("PENTART");
  const [altTextPolicy, setAltTextPolicy] = useState<"preserve" | "approved_overwrite">("preserve");

  const selectedIds = useMemo(() => {
    if (selection.selectedIds.length > 0) return selection.selectedIds;
    return selectedRows.map((row) => row.id);
  }, [selection.selectedIds, selectedRows]);

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    mutation.mutate({
      supplier_code: supplierCode,
      supplier_verified: true,
      selection: {
        scope_mode: selection.scopeMode,
        total_matching: selection.totalMatching,
        selection_token: selection.selectionToken,
        selected_ids: selectedIds,
      },
      action_blocks: [
        {
          operation,
          field_name: fieldName,
          value,
        },
      ],
      apply_mode: "immediate",
      alt_text_policy: altTextPolicy,
    });
  }

  return (
    <section className="panel" data-testid="bulk-action-builder">
      <h2 className="forensic-card-title">Bulk Action Builder</h2>
      <p className="forensic-card-copy">
        Operation-first staging with admission checks before apply.
      </p>
      <form onSubmit={handleSubmit} className="forensic-control-grid">
        <label className="forensic-field">
          <span className="forensic-field-label">Supplier code</span>
          <input value={supplierCode} onChange={(event) => setSupplierCode(event.target.value)} />
        </label>
        <label className="forensic-field">
          <span className="forensic-field-label">Operation</span>
          <select value={operation} onChange={(event) => setOperation(event.target.value as (typeof OPERATIONS)[number])}>
            {OPERATIONS.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
        <label className="forensic-field">
          <span className="forensic-field-label">Field</span>
          <select value={fieldName} onChange={(event) => setFieldName(event.target.value as (typeof MUTABLE_FIELDS)[number])}>
            {MUTABLE_FIELDS.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
        <label className="forensic-field">
          <span className="forensic-field-label">Value</span>
          <input value={value} onChange={(event) => setValue(event.target.value)} />
        </label>
        <label className="forensic-field">
          <span className="forensic-field-label">Alt-text policy</span>
          <select
            value={altTextPolicy}
            onChange={(event) => setAltTextPolicy(event.target.value as "preserve" | "approved_overwrite")}
          >
            <option value="preserve">preserve</option>
            <option value="approved_overwrite">approved_overwrite</option>
          </select>
        </label>
        <p className="bulk-builder-locked">
          <strong>Protected fields</strong>:{" "}
          {LOCKED_FIELDS.map((field) => (
            <code key={field} data-protected-field={field}>
              {field}
            </code>
          ))}
        </p>
        <button className="btn-primary" type="submit" disabled={mutation.isPending || selectedIds.length === 0}>
          Stage action block
        </button>
      </form>

      <ApprovalBlockCard
        title="Admission Outcome"
        admission={mutation.data?.admission ?? null}
      />
      {mutation.error ? <p style={{ color: "var(--error)" }}>Staging failed.</p> : null}
      {mutation.data ? (
        <p className="muted" data-testid="staging-result">
          Batch #{mutation.data.batch_id} created ({mutation.data.counts.staged_rows} staged rows)
        </p>
      ) : null}
    </section>
  );
}
