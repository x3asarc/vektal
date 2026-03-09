# Sentry Redis/Celery Issues Analysis

## Issue Summary

### Issue #101522185 - Connection to Redis Lost
- **Title**: Connection to Redis lost: Retry (8/20) in 1.00 second.
- **Project**: synthex-workers
- **Count**: 713 events
- **Status**: Unresolved
- **Severity**: High (high frequency)

### Issue #101522288 - Retry Limit Exceeded
- **Title**: Retry limit exceeded while trying to reconnect to the Celery redis result store backend. The Celery application must be restarted.
- **Project**: synthex-workers
- **Count**: 35 events
- **Status**: Unresolved
- **Severity**: Critical (requires restart)

## Initial Hypothesis

Based on the Sentry data and existing `scripts/sentry/fix_redis_connections.py`:
1. Redis connection pool not properly configured
2. Missing broker_transport_options
3. No socket timeout/keepalive settings
4. Insufficient retry backoff configuration

## Files to Investigate

From `fix_redis_connections.py` analysis:
- `src/celery_app.py` - Celery configuration
- `src/config.py` - Redis URL configuration
- Related workers/tasks that might be creating excessive connections

## Next Steps

1. Query Aura graph for blast radius around:
   - `src/celery_app.py`
   - Redis connection usage
   - Celery task definitions
2. Trace impact radius to understand all affected components
3. Forensic analysis of connection pooling configuration
