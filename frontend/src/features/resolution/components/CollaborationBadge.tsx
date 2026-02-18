"use client";

type CollaborationBadgeProps = {
  locked: boolean;
  lockOwnerUserId?: number | null;
  readOnly: boolean;
};

export function userColor(userId?: number | null) {
  if (!userId) return "var(--muted)";
  return userId % 2 === 0 ? "#1455b8" : "#1e7f2f";
}

export function CollaborationBadge({
  locked,
  lockOwnerUserId,
  readOnly,
}: CollaborationBadgeProps) {
  if (!locked) {
    return <p className="muted">Batch checkout: available</p>;
  }

  return (
    <p
      style={{
        margin: 0,
        padding: "8px 10px",
        borderRadius: 8,
        border: "1px solid var(--border)",
        background: "var(--surface)",
      }}
      data-testid="collaboration-badge"
    >
      <strong>Batch checkout:</strong>{" "}
      <span style={{ color: userColor(lockOwnerUserId) }}>
        User {lockOwnerUserId ?? "unknown"}
      </span>{" "}
      is currently reviewing this.
      {readOnly ? " You are in read-only mode." : ""}
    </p>
  );
}
