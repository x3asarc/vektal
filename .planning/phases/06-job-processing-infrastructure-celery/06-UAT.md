# 06 UAT Checklist

status: completed
phase: 06
updated: 2026-02-10

## Checklist

- [x] Start stack (`docker compose up -d`) and confirm `backend`, `celery_worker`, `celery_scraper`, `flower`, `redis`, `db` are healthy.
- [x] Open Flower at `http://localhost:5555` and verify worker/queue visibility.
- [x] Launch a new ingest job through `/api/v1/jobs` and confirm immediate `202` response.
- [x] Verify progress updates over `/api/v1/jobs/<id>/stream` and `/status`.
- [x] Trigger cancellation and verify `cancel_requested` then `cancelled` convergence.
- [x] Confirm requirement matrix in `06-VERIFICATION.md` is complete and accurate.

## Approval

- approved
