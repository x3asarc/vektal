import { JobsWorkspace } from "@/features/jobs/components/JobsWorkspace";

export const JOBS_PAGE_SECTIONS = [
  "jobs-summary",
  "jobs-list",
] as const;

export default function JobsPage() {
  return <JobsWorkspace />;
}

