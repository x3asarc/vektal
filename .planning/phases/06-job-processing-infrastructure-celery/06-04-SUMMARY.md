# 06-04 Summary: Dispatcher and Finalizer Convergence

## Completed
- Implemented lock-safe dispatcher:
  - `src/jobs/dispatcher.py`
  - `src/tasks/audits.py`
- Implemented terminal convergence logic:
  - `src/jobs/finalizer.py`
  - `src/tasks/control.py` (finalizer task entrypoint)

## Behavior Delivered
- `FOR UPDATE SKIP LOCKED` claim flow for pending checkpoint outbox rows.
- Durable retry scheduling with backoff (`next_dispatch_at`, attempt tracking).
- Finalizer transitions:
  - `running -> completed|failed_terminal`
  - `cancel_requested -> cancelled`
- Strict failure mode is default; lenient mode remains configurable.

