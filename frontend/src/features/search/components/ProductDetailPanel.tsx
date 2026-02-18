"use client";

type ProductDetailPanelProps = {
  product: {
    id: number;
    title: string | null;
    sku: string | null;
    barcode: string | null;
    vendor_code: string | null;
    status: string | null;
    price: number | null;
    description?: string | null;
    tags?: string[] | null;
  } | null;
};

export function ProductDetailPanel({ product }: ProductDetailPanelProps) {
  if (!product) {
    return (
      <section className="panel" data-testid="product-detail-panel">
        <h2>Product Detail</h2>
        <p className="muted">Select a product to inspect complete details.</p>
      </section>
    );
  }

  return (
    <section className="panel" data-testid="product-detail-panel">
      <h2>Product Detail</h2>
      <p className="muted">Lineage-ready view for precision review.</p>
      <dl style={{ display: "grid", gridTemplateColumns: "140px 1fr", gap: 8, margin: 0 }}>
        <dt>ID</dt>
        <dd>{product.id}</dd>
        <dt>Title</dt>
        <dd>{product.title ?? "-"}</dd>
        <dt>SKU</dt>
        <dd>{product.sku ?? "-"}</dd>
        <dt>Barcode</dt>
        <dd>{product.barcode ?? "-"}</dd>
        <dt>Vendor</dt>
        <dd>{product.vendor_code ?? "-"}</dd>
        <dt>Status</dt>
        <dd>{product.status ?? "-"}</dd>
        <dt>Price</dt>
        <dd>{typeof product.price === "number" ? `$${product.price.toFixed(2)}` : "-"}</dd>
      </dl>
      <h3 style={{ marginBottom: 6 }}>Description</h3>
      <p>{product.description ?? "-"}</p>
      <h3 style={{ marginBottom: 6 }}>Tags</h3>
      <p>{(product.tags ?? []).length > 0 ? (product.tags ?? []).join(", ") : "-"}</p>
    </section>
  );
}
