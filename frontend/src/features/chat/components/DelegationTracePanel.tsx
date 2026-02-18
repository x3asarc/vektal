"use client";

import { useMemo, useState } from "react";

type DelegationTrace = {
  delegation_event_id?: number;
  status?: string;
  worker_tool_scope?: string[];
  blocked_tools?: string[];
  task_id?: string | null;
  queue?: string | null;
  reason?: string | null;
};

type DelegationTracePanelProps = {
  trace: DelegationTrace | null | undefined;
};

function asTrace(value: unknown): DelegationTrace | null {
  if (!value || typeof value !== "object") return null;
  return value as DelegationTrace;
}

export function DelegationTracePanel({ trace }: DelegationTracePanelProps) {
  const [expanded, setExpanded] = useState(false);
  const data = asTrace(trace);
  const summary = useMemo(() => {
    if (!data) return "No delegation trace";
    const status = data.status ?? "unknown";
    const scopeCount = Array.isArray(data.worker_tool_scope) ? data.worker_tool_scope.length : 0;
    return `Delegation ${status} (${scopeCount} tools)`;
  }, [data]);

  if (!data) return null;

  return (
    <section className="panel delegation-trace" data-testid="delegation-trace">
      <button
        type="button"
        className="delegation-trace-toggle"
        onClick={() => setExpanded((prev) => !prev)}
      >
        {expanded ? "Hide Trace" : "View Trace"} - {summary}
      </button>
      {expanded && (
        <pre className="delegation-trace-body">
          {JSON.stringify(
            {
              delegation_event_id: data.delegation_event_id,
              status: data.status,
              queue: data.queue,
              task_id: data.task_id,
              worker_tool_scope: data.worker_tool_scope ?? [],
              blocked_tools: data.blocked_tools ?? [],
              reason: data.reason ?? null,
            },
            null,
            2,
          )}
        </pre>
      )}
    </section>
  );
}
