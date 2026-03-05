"use client";

type OperationalErrorCardProps = {
  title: string;
  detail: string;
  diagnosticId?: string;
  retryLabel?: string;
  onRetry?: () => void;
  secondaryLabel?: string;
  onSecondaryAction?: () => void;
};

export function OperationalErrorCard({
  title,
  detail,
  diagnosticId,
  retryLabel = "Retry",
  onRetry,
  secondaryLabel,
  onSecondaryAction,
}: OperationalErrorCardProps) {
  return (
    <section className="ops-error-card" role="alert">
      <div className="ops-error-head">
        <strong>{title}</strong>
        {diagnosticId ? <code>diag:{diagnosticId}</code> : null}
      </div>
      <p>{detail}</p>
      <div className="ops-error-actions">
        {onRetry ? (
          <button className="btn-primary" type="button" onClick={onRetry}>
            {retryLabel}
          </button>
        ) : null}
        {onSecondaryAction && secondaryLabel ? (
          <button className="btn-ghost" type="button" onClick={onSecondaryAction}>
            {secondaryLabel}
          </button>
        ) : null}
      </div>
    </section>
  );
}
