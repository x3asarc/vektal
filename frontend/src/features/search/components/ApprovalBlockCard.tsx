"use client";

type ApprovalBlockCardProps = {
  title: string;
  admission: {
    schema_ok: boolean;
    policy_ok: boolean;
    conflict_state: "none" | "warning" | "blocked";
    eligible_to_apply: boolean;
    reasons: string[];
  } | null;
};

function boolLabel(flag: boolean): string {
  return flag ? "PASS" : "FAIL";
}

export function ApprovalBlockCard({ title, admission }: ApprovalBlockCardProps) {
  return (
    <article className="panel" data-testid="approval-block-card">
      <h3>{title}</h3>
      {!admission ? (
        <p className="muted">Admission result pending.</p>
      ) : (
        <>
          <p className="muted">Action-block approval gate status.</p>
          <ul style={{ marginTop: 6 }}>
            <li>Schema: {boolLabel(admission.schema_ok)}</li>
            <li>Policy: {boolLabel(admission.policy_ok)}</li>
            <li>Conflict state: {admission.conflict_state}</li>
            <li>Eligible to apply: {boolLabel(admission.eligible_to_apply)}</li>
          </ul>
          {admission.reasons.length > 0 ? (
            <>
              <h4 style={{ marginBottom: 6 }}>Reasons</h4>
              <ul>
                {admission.reasons.map((reason) => (
                  <li key={reason}>{reason}</li>
                ))}
              </ul>
            </>
          ) : null}
        </>
      )}
    </article>
  );
}
