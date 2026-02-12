"use client";

import { useMemo } from "react";
import { useParams } from "next/navigation";
import { useJobDetailObserver } from "@/features/jobs/hooks/useJobDetailObserver";

export default function JobDetailPage() {
  const params = useParams<{ id?: string | string[] }>();
  const id = useMemo(() => {
    if (!params?.id) return null;
    return Array.isArray(params.id) ? params.id[0] : params.id;
  }, [params]);

  const observed = useJobDetailObserver(id);

  return (
    <main>
      <h1>Job {id ?? "unknown"}</h1>
      <p className="muted">
        SSE-first observation with polling fallback is active.
      </p>
      <p className="muted">
        Transport mode: <strong>{observed.mode}</strong>
      </p>
      {observed.degraded && (
        <p className="muted">
          Transport degraded: polling fallback also failed.
        </p>
      )}
      {observed.job && (
        <p className="muted">
          Current backend status: <strong>{observed.job.status}</strong>
        </p>
      )}
    </main>
  );
}
