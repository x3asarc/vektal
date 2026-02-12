"use client";

import { useCallback, useEffect, useState } from "react";
import { apiRequest } from "@/lib/api/client";
import { isActiveBackendStatus } from "@/features/jobs/observer/job-observer";

export type JobListItem = {
  id: number;
  status: string;
  job_name?: string;
  error_message?: string | null;
};

type JobsResponse = {
  jobs: JobListItem[];
  total: number;
};

export function selectActiveJobs(jobs: JobListItem[]): JobListItem[] {
  return jobs.filter((job) => isActiveBackendStatus(job.status));
}

export function useJobRehydrate() {
  const [jobs, setJobs] = useState<JobListItem[]>([]);
  const [activeJobs, setActiveJobs] = useState<JobListItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isRehydrating, setIsRehydrating] = useState(false);
  const [rehydrateCount, setRehydrateCount] = useState(0);

  const rehydrate = useCallback(async () => {
    setIsRehydrating(true);
    try {
      const response = await apiRequest<JobsResponse>("/api/v1/jobs?limit=50");
      setJobs(response.jobs);
      setActiveJobs(selectActiveJobs(response.jobs));
      setError(null);
      setRehydrateCount((count) => count + 1);
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Failed to rehydrate jobs.");
      }
    } finally {
      setIsRehydrating(false);
    }
  }, []);

  useEffect(() => {
    void rehydrate();

    const onRefreshTrigger = () => {
      void rehydrate();
    };

    window.addEventListener("focus", onRefreshTrigger);
    window.addEventListener("online", onRefreshTrigger);

    return () => {
      window.removeEventListener("focus", onRefreshTrigger);
      window.removeEventListener("online", onRefreshTrigger);
    };
  }, [rehydrate]);

  return {
    jobs,
    activeJobs,
    error,
    isRehydrating,
    rehydrateCount,
    rehydrate,
  };
}
