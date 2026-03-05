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
        <h2 className="forensic-card-title">Product Detail</h2>
        <p className="forensic-card-copy">Select a product to inspect complete details.</p>
      </section>
    );
  }

  return (
    <section className="panel" data-testid="product-detail-panel">
      <h2 className="forensic-card-title">Product Detail</h2>
      <p className="forensic-card-copy">Lineage-ready view for precision review.</p>
      <dl className="search-detail-grid">
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
      <h3 className="forensic-card-title" style={{ marginTop: 8 }}>Description</h3>
      <p className="forensic-card-copy">{product.description ?? "-"}</p>
      <h3 className="forensic-card-title" style={{ marginTop: 8 }}>Tags</h3>
      <p className="forensic-card-copy">{(product.tags ?? []).length > 0 ? (product.tags ?? []).join(", ") : "-"}</p>
    </section>
  );
}
