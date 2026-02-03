# Pitfalls Research

**Domain:** Dockerized Flask Microservices Production Deployment
**Researched:** 2026-02-03
**Confidence:** MEDIUM-HIGH

## Critical Pitfalls

### Pitfall 1: Using Flask Development Server in Production

**What goes wrong:**
The Flask development server is explicitly not designed for production use. It doesn't handle parallel execution, networking, or concurrent requests properly, leading to blocked requests, poor performance, and potential crashes under load.

**Why it happens:**
Developers containerize their existing development setup without changing the server configuration. The `flask run` command or `app.run()` works locally, so they assume Docker will make it production-ready.

**How to avoid:**
- Use a production WSGI server (Gunicorn or uWSGI) in your Dockerfile
- Configure worker processes appropriately: `(2 × number_of_cores) + 1` as starting point
- For long-running connections or WebSockets, use async workers (gevent/eventlet)
- Add nginx as reverse proxy layer for static files and load balancing

**Warning signs:**
- Dockerfile has `CMD ["flask", "run"]` or `CMD ["python", "app.py"]`
- Single-threaded performance degrades immediately under concurrent load
- Console shows "This is a development server. Do not use it in a production deployment" warning

**Phase to address:**
Phase 1 (Containerization Setup) - Must be configured before any service goes to production

---

### Pitfall 2: Encryption Key Loss During SQLite to PostgreSQL Migration

**What goes wrong:**
Credentials and sensitive data encrypted with a specific key in SQLite become permanently inaccessible if the encryption key is lost during migration. The entire migration fails or completes with corrupted encrypted fields, breaking authentication and external API integrations.

**Why it happens:**
Teams focus on data schema migration but overlook that encryption keys are environment-specific. When setting up new PostgreSQL containers, they generate new keys or use different `.env` files, making old encrypted data unreadable.

**How to avoid:**
- Document all encryption keys BEFORE starting migration
- Back up complete `.env` files from production SQLite environment
- Test decryption of encrypted fields (API keys, passwords) in staging before production migration
- Use a secrets management system (HashiCorp Vault, AWS Secrets Manager) to centralize key storage
- Verify encrypted credentials work after migration with test API calls

**Warning signs:**
- Authentication fails after migration despite user data being present
- External API integrations (Shopify, OpenAI, Gemini) fail with credential errors
- Database shows data in encrypted columns but application can't decrypt it

**Phase to address:**
Phase 2 (Database Migration) - Critical pre-migration checklist item

---

### Pitfall 3: Environment Variables Exposing Secrets in Production

**What goes wrong:**
Secrets stored as environment variables are visible in plain text through `docker inspect`, `/proc/[pid]/environ`, logs, crash dumps, and debugging tools. A single compromised host or container exposes all API keys, database passwords, and authentication tokens.

**Why it happens:**
Environment variables are the easiest way to configure containers and work perfectly in development. Teams don't realize that Docker environment variables lack access control, audit trails, rotation capabilities, and are "set and forget" with no management.

**How to avoid:**
- Use Docker Secrets (Swarm) or Kubernetes Secrets for sensitive values
- Implement external secrets manager (HashiCorp Vault, Doppler, AWS Secrets Manager)
- Use file-based secret mounts instead of environment variables
- Never embed secrets in images or build arguments
- Implement different secrets per environment (dev, staging, production)
- Enable TLS for log transmissions and enforce access controls

**Warning signs:**
- `.env` files committed to git (even if gitignored, they might be in history)
- `docker inspect <container>` shows API keys and passwords
- Environment variables never rotated since initial deployment
- Logs contain "Bearer tokens" or API keys in error traces
- No audit trail of who accessed which secrets

**Phase to address:**
Phase 1 (Containerization Setup) - Must be designed into architecture from start

---

### Pitfall 4: Monolithic Design Patterns Applied to Microservices

**What goes wrong:**
Teams split their monolithic Flask app into containers but maintain tight coupling through shared databases, in-process communication patterns, and global state. This creates "distributed monolith" with microservices disadvantages (network latency, complexity) and none of the advantages (independent deployment, scaling).

**Why it happens:**
Migration focuses on containerization rather than architectural redesign. Developers assume splitting code into separate Docker containers equals microservices architecture without addressing shared data models, synchronous dependencies, and coupling.

**How to avoid:**
- Define clear service boundaries based on business capabilities (scraping, API, frontend, workers)
- Each microservice owns its database schema - no shared database access
- Use async communication (message queues, events) for service-to-service calls where possible
- Implement API contracts between services rather than shared Python imports
- Design for independent deployment - services should not require coordinated releases
- Apply database-per-service pattern or schema-per-service at minimum

**Warning signs:**
- Multiple services directly query the same PostgreSQL tables
- Changing one service requires coordinating deploys of other services
- Services import Python modules from other services
- Single database migration affects multiple services
- Cannot scale services independently due to tight coupling

**Phase to address:**
Phase 1 (Architecture Planning) - Must define service boundaries before containerization

---

### Pitfall 5: Missing Health Checks and Restart Loop Hell

**What goes wrong:**
Containers restart infinitely due to missing health checks, incorrect restart policies, or dependencies not being ready. The "always" restart policy causes a container that never starts successfully to enter restart loops, consuming resources and preventing debugging.

**Why it happens:**
Teams deploy containers without implementing health check endpoints or proper startup validation. Docker restart policies are configured without understanding their behavior, and services don't wait for dependencies (database, message queue) to be ready before attempting connections.

**How to avoid:**
- Implement `/health` and `/ready` endpoints in Flask applications
- Configure Dockerfile HEALTHCHECK with appropriate intervals and retries
- Use `unless-stopped` restart policy for most production cases (not `always`)
- Implement startup probes that check database connectivity before marking ready
- Add dependency health checks in docker-compose (healthcheck, depends_on condition)
- Ensure containers must be up for at least 10 seconds before restart monitoring begins

**Warning signs:**
- `docker ps` shows containers constantly restarting (STATUS: "Restarting (1) 5 seconds ago")
- Container logs show repeated initialization failures
- Database connection errors on startup without retry logic
- No health check endpoint returns 200 OK
- Manual `docker stop` followed by daemon restart causes unwanted container start

**Phase to address:**
Phase 1 (Containerization Setup) - Every service needs health checks from deployment day one

---

### Pitfall 6: Gunicorn/uWSGI Worker Misconfiguration

**What goes wrong:**
Using default single worker causes requests to block. Using too many workers exhausts database connections or memory. Using sync workers for long-running scraping tasks blocks all other requests. Global variables in Flask app behave inconsistently across workers, breaking session management and state.

**Why it happens:**
Production WSGI server documentation is skimmed, defaults are used without understanding implications. The formula `(2 × cores) + 1` is applied blindly without considering workload characteristics (sync vs async, long vs short requests).

**How to avoid:**
- Configure worker count based on workload: `(2 × cores) + 1` for sync workers
- Use async workers (gevent/eventlet) for I/O-bound tasks, scraping, or long-running connections
- Avoid global variables - use Flask-Session with Redis for session state across workers
- Set appropriate worker timeouts for scraping operations
- Monitor worker restart frequency and memory usage per worker
- Don't run application as root - configure user in Dockerfile

**Warning signs:**
- High response times under moderate load with low CPU usage
- Inconsistent behavior between requests (decorators, sessions working intermittently)
- Database connection pool exhaustion with few actual requests
- Workers killed by timeout on legitimate long-running scraping tasks
- Memory usage grows unbounded in worker processes

**Phase to address:**
Phase 1 (Containerization Setup) and Phase 4 (Performance Optimization) - Initial config in Phase 1, tuning in Phase 4

---

### Pitfall 7: Database Connection Pool Exhaustion Across Containers

**What goes wrong:**
PostgreSQL has a connection limit (default 100). Multiple containerized services each create connection pools, quickly exhausting available connections. Scraping workers, API servers, and background jobs all compete for connections, leading to "too many connections" errors and service failures.

**Why it happens:**
Each service configures its own SQLAlchemy pool (default pool_size=5, max_overflow=10) without considering total system connections. Formula: `(pool_size + max_overflow) × number_of_containers` easily exceeds `max_connections=100`.

**How to avoid:**
- Calculate total connection budget: `max_connections / number_of_services`
- Configure SQLAlchemy pools conservatively: `pool_size=2-5` per container
- Implement PgBouncer as sidecar container for connection pooling
- Set `pool_recycle` to prevent stale connections in containerized environments
- Monitor active PostgreSQL connections: `SELECT count(*) FROM pg_stat_activity;`
- Increase PostgreSQL `max_connections` if needed (requires more shared_buffers)
- Configure pool timeouts and proper connection closing

**Warning signs:**
- "FATAL: remaining connection slots are reserved" errors
- Services fail to start with connection errors despite database being healthy
- `pg_stat_activity` shows many idle connections
- Connection errors increase linearly with container scaling
- Database CPU is low but connection errors are high

**Phase to address:**
Phase 2 (Database Migration) - Design connection strategy during PostgreSQL setup

---

### Pitfall 8: Logging to Container Filesystem Instead of stdout/stderr

**What goes wrong:**
Application logs written to files inside containers are lost when containers restart. No centralized logging means debugging requires accessing individual containers. Log files fill container storage, causing crashes. Critical errors disappear when containers are recreated.

**Why it happens:**
Flask logging is configured for traditional server deployment with FileHandler writing to `/var/log/app.log`. Docker best practice of logging to stdout/stderr is overlooked because file-based logging "just works" in development.

**How to avoid:**
- Configure Flask logging to write access logs to `/dev/stdout` and error logs to `/dev/stderr`
- Use Docker json-file driver with log rotation (max-size: 10MB, max-file: 5)
- Implement centralized logging with Fluentd or syslog driver forwarding to remote server
- Use structured JSON logging for better parsing in log aggregation systems
- Configure async logging mode for better performance
- Tag logs with service name for microservices environments

**Warning signs:**
- Cannot find logs after container restart
- `docker logs <container>` shows no output or only server startup messages
- Disk usage alerts from containers storing large log files
- No way to search logs across all services
- Debugging requires manually SSH'ing into containers

**Phase to address:**
Phase 1 (Containerization Setup) - Logging architecture must be designed from start

---

### Pitfall 9: Continuing Monolith Development During Migration

**What goes wrong:**
The migration to microservices takes months. During this time, the monolithic production app receives bug fixes and new features. These changes aren't ported to the microservices version, causing divergence. When migration completes, the new system is outdated and missing critical fixes.

**Why it happens:**
Business cannot pause feature development during migration. Teams underestimate migration duration and don't establish parallel development strategy. Code changes go to "what's in production" which is still the monolith.

**How to avoid:**
- Use Strangler Fig pattern - gradually replace monolith pieces while maintaining single deployment
- Establish branch strategy - backport critical fixes to microservices branch
- Deploy microservices behind feature flags for gradual rollout
- Create shared library for business logic used by both monolith and microservices
- Set hard deadline - if migration exceeds 3-6 months, reconsider approach
- Communicate clearly which version (monolith vs microservices) receives which changes

**Warning signs:**
- Migration timeline extends beyond 6 months
- Git branches for microservices haven't merged in weeks
- Bug reported in production (monolith) isn't present in microservices branch
- Feature requests go to monolith "because it's faster"
- Team unsure which codebase is "source of truth"

**Phase to address:**
Phase 0 (Migration Planning) - Strategy must be defined before any work begins

---

### Pitfall 10: Missing Rate Limiting and Circuit Breakers for External APIs

**What goes wrong:**
Shopify API hits rate limits and blocks requests. OpenAI/Gemini API costs skyrocket due to retry storms. Vendor websites detect scraping patterns and ban IP addresses. When external APIs fail, services crash or hang instead of degrading gracefully.

**Why it happens:**
Monolithic app had rate limiting built into single-threaded execution. Microservices scale horizontally, multiplying API calls. Teams focus on internal microservices communication but overlook external API integration patterns.

**How to avoid:**
- Implement rate limiting at service level respecting external API limits
- For Shopify: Honor `X-Shopify-Shop-Api-Call-Limit` headers, implement leaky bucket algorithm
- For OpenAI/Gemini: Set budget caps, implement token counting, use exponential backoff
- For scraping: Implement per-vendor rate limiting, rotate user agents, use delays between requests
- Add circuit breakers - if external API fails X times, stop calling for Y duration
- Implement retry logic with exponential backoff and jitter
- Monitor API costs and rate limit status as key metrics

**Warning signs:**
- 429 (Too Many Requests) errors in logs
- Unexpected API bills (OpenAI/Gemini costs exceed budget)
- Vendor websites returning CAPTCHAs or blocking requests
- Services hang waiting for external API responses
- No visibility into external API success rates or costs
- Retry logic causes thundering herd problem

**Phase to address:**
Phase 3 (External Integration Setup) - Must be implemented before production traffic

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Shared database across services | Faster initial migration, no data synchronization needed | Cannot deploy services independently, tight coupling, migration difficulties | Never - undermines entire microservices architecture |
| Using Alpine base images | Smaller image size (5MB vs 50MB) | Python wheel compatibility issues with musl libc, harder debugging, longer build times | Only if image size is critical constraint and wheels are tested |
| Skipping multi-stage Docker builds | Simpler Dockerfile, faster initial setup | 50% larger images, build tools in production, security vulnerabilities | Only for proof-of-concept, never for production |
| Single docker-compose.yml for all environments | One configuration to maintain | Cannot customize per environment, secrets mixed with non-secrets | Acceptable for dev/staging if production uses orchestration |
| Environment variables for secrets | Quick setup, works immediately | Security vulnerabilities, no rotation, audit trail, or access control | Only in local development, never staging/production |
| Running containers as root | Avoids permission issues | Security vulnerability if container compromised | Never acceptable in production |
| Single PostgreSQL instance for all microservices | Simpler infrastructure, lower cost | Connection pool exhaustion, service coupling, blast radius of failures | Only for small deployments (<5 services, <100 concurrent users) |

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Shopify API | Not checking rate limit headers, syncing all products every request | Respect X-Shopify-Shop-Api-Call-Limit, use webhooks for updates, implement leaky bucket |
| OpenAI/Gemini | No token counting, unlimited retries, no streaming | Count tokens before API call, set budget caps, stream responses, implement exponential backoff |
| Vendor Scraping | Same user agent for all requests, no delays, fixed IP | Rotate user agents, randomize delays (2-10s), respect robots.txt, use proxy rotation if needed |
| PostgreSQL | Creating new connection per request | Use connection pooling (SQLAlchemy), configure pool_recycle for containers |
| Message Queue (Redis/Celery) | No task timeouts, unlimited retries | Set task time_limit, max_retries=3, implement idempotent task design |
| Docker Network | Using container IPs instead of service names | Use Docker service discovery (service names), never hardcode IPs |
| .env Files | Committing to git, same file for all environments | Use .env.example template, gitignore .env, separate files per environment |

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Synchronous scraping in API request | Slow API responses, timeouts | Use Celery workers for scraping, return job ID, poll for results | >5 concurrent scrape requests |
| No connection pooling | "Too many connections" errors under load | Configure SQLAlchemy pool_size and max_overflow appropriately | >50 concurrent users |
| Single worker per service | Request blocking, poor throughput | Configure multiple Gunicorn workers: (2 × cores) + 1 | >10 requests/second |
| Sync workers for I/O-bound tasks | High latency despite low CPU | Use gevent/eventlet workers for scraping and API calls | >20 concurrent long-running requests |
| No database indexes after migration | Slow queries, high CPU | Add indexes for foreign keys, frequently queried columns | >10k products in database |
| Unbounded task queues | Memory exhaustion, lost jobs | Set Celery max tasks per worker, implement queue length monitoring | >1000 pending jobs |
| Container storage for uploads | Lost files on restart, disk exhaustion | Use volumes or external storage (S3, MinIO) | Any production deployment |

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| API keys in environment variables | Exposed via docker inspect, logs, crash dumps | Use Docker Secrets, external secrets manager, file-based mounts |
| Running containers as root | Privilege escalation if container compromised | Create non-root user in Dockerfile, use USER directive |
| No network segmentation | Compromised service accesses entire infrastructure | Use Docker networks to isolate services, apply least privilege |
| Vendor credentials in code | Credential leakage in git history, logs | Store in secrets manager, inject at runtime, never commit |
| No HTTPS for internal services | Man-in-the-middle attacks between containers | Use TLS for inter-service communication, even within Docker network |
| Unencrypted database backups | Data breach if backup storage compromised | Encrypt backups, use pg_dump with encryption, secure storage |
| Fixed secrets across environments | Production compromise exposes dev/staging | Different secrets per environment, rotate regularly |
| Scraping without rate limiting | IP bans, legal risks, vendor detection | Respect robots.txt, implement delays, rotate IPs if needed |

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Synchronous scraping | 30+ second page loads, timeouts | Async jobs with progress indicators, webhook notifications |
| No job status visibility | Users don't know if scraping worked | Real-time status dashboard, job completion notifications |
| Generic error messages | Cannot debug issues ("Something went wrong") | Specific errors: "Vendor site timeout", "Rate limit exceeded", "SKU not found" |
| No scraping history | Cannot track what changed or when | Log every scrape attempt with timestamp, success/failure, data changes |
| All-or-nothing deployments | Entire platform down during deploys | Rolling updates, blue-green deployment, zero-downtime releases |
| No cost visibility | Surprise API bills | Real-time cost dashboard showing OpenAI/Gemini API usage |
| No bulk operations | Users must trigger 4000 SKU scrapes individually | Batch operations, scheduled scraping, vendor-level triggers |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Containerization:** Docker builds locally - verify it works in production environment (different network, volumes, permissions)
- [ ] **Database migration:** Data imported successfully - verify encrypted credentials decrypt correctly and test with API calls
- [ ] **Health checks:** Service starts successfully - verify /health endpoint checks database connectivity, not just process running
- [ ] **Logging:** Can see logs with docker logs - verify logs persist after container restart, centralized logging configured
- [ ] **Secrets management:** API keys work in dev - verify production uses secrets manager, not environment variables
- [ ] **Service discovery:** Services communicate in docker-compose - verify works with dynamic IPs, DNS resolution, multiple replicas
- [ ] **Worker scaling:** Single Celery worker processes jobs - verify multiple workers don't cause race conditions, duplicate jobs
- [ ] **Rate limiting:** Respects limits during testing - verify handles burst traffic, multiple services calling same API
- [ ] **Connection pooling:** Database queries work - verify connections released properly, pool doesn't exhaust under load
- [ ] **Error handling:** Catches exceptions - verify partial failures (1 vendor down) don't crash entire system
- [ ] **Monitoring:** Can view logs - verify metrics exported (success rates, durations, costs), alerts configured
- [ ] **Backups:** Database backup command works - verify restore process tested, backups encrypted, automated schedule

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Lost encryption keys | HIGH | No recovery possible - must regenerate all encrypted credentials, re-enter API keys manually |
| Secrets in git history | MEDIUM | Rotate all exposed secrets immediately, use git-filter-repo to clean history, audit access logs |
| Connection pool exhaustion | LOW | Restart services, reduce pool sizes in config, add PgBouncer, increase PostgreSQL max_connections |
| Monolith divergence | HIGH | Backport changes manually (weeks of work), establish regression test suite, consider restarting migration |
| Rate limit bans | MEDIUM | Wait for ban expiration (24h - 7d), rotate IPs, contact vendor support, implement proper rate limiting |
| Container restart loops | LOW | Check logs, fix startup issue (usually database/dependency not ready), adjust health check timing |
| No centralized logging | MEDIUM | Deploy logging stack (Fluentd/ELK), reconfigure services, accept historical logs are lost |
| Distributed monolith | HIGH | Refactor service boundaries (months), implement async communication, separate databases |
| Worker misconfiguration | LOW | Adjust worker count/type in config, restart service, monitor performance metrics |
| Missing circuit breakers | MEDIUM | Add circuit breaker library (pybreaker), configure thresholds, deploy updated services |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Development server in production | Phase 1: Containerization | Dockerfile uses gunicorn/uwsgi, docker ps shows production server process |
| Encryption key loss | Phase 2: Database Migration | Test decryption of sample encrypted credential, successful API call with migrated key |
| Environment variable secrets | Phase 1: Containerization | docker inspect shows no secrets, secrets file mounted instead |
| Monolithic design patterns | Phase 1: Architecture | Services use separate databases, API contracts defined, no shared code imports |
| Missing health checks | Phase 1: Containerization | curl /health returns 200, healthcheck configured in Dockerfile |
| Worker misconfiguration | Phase 1: Containerization | Gunicorn/uWSGI config specifies worker count and type, tested under load |
| Connection pool exhaustion | Phase 2: Database Migration | SQLAlchemy pool configured, total connections < max_connections, load tested |
| Logging to filesystem | Phase 1: Containerization | docker logs shows application logs, centralized logging receives messages |
| Monolith divergence | Phase 0: Planning | Migration strategy documented, feature freeze or backport process defined |
| Missing API protections | Phase 3: External Integration | Rate limiters active, circuit breakers tested, cost monitoring dashboard live |

## Sources

### Containerization and Deployment
- [Build and Deploy a REST API Microservice with Python Flask and Docker - DEV Community](https://dev.to/swarnimwalavalkar/build-and-deploy-a-rest-api-microservice-with-python-flask-and-docker-5c2d)
- [Dockerizing Flask Microservices for Deployment - Mike Bridge](https://mikebridge.github.io/post/python-flask-kubernetes-3/)
- [Running Flask on Docker Swarm | TestDriven.io](https://testdriven.io/blog/running-flask-on-docker-swarm/)
- [Docker and Containers 2026: Python Containerization and the Cloud-Native Tipping Point](https://www.programming-helper.com/tech/docker-containers-2026-python-containerization-cloud-native)

### Migration Challenges
- [9 Most Common Mistakes when Migrating from Monolith to Microservices – NG Logic](https://nglogic.com/9-most-common-mistakes-when-migrating-from-monolith-to-microservices/)
- [Overcoming Monolith-to-Microservices Migration Challenges](https://hqsoftwarelab.com/blog/migrating-monolithic-to-microservices-challenges/)
- [Monolith to Microservices: 5 Strategies, Challenges and Solutions](https://komodor.com/learn/monolith-to-microservices-5-strategies-challenges-and-solutions/)

### Database Migration
- [Issues with migration from Default SQLite to PostgreSQL in n8n Docker Deployment](https://community.n8n.io/t/issues-with-migration-from-default-sqlite-to-postgresql-in-n8n-docker-deployment/35903)
- [Database Migration: Transitioning from SQLite to PostgreSQL on AWS](https://medium.com/@kagegreo/database-migration-transitioning-from-sqlite-to-postgresql-on-aws-e84f0b79430e)
- [Database Migration: SQLite to PostgreSQL](https://www.bytebase.com/blog/database-migration-sqlite-to-postgresql/)

### Production Server Configuration
- [Gunicorn — Flask Documentation (3.1.x)](https://flask.palletsprojects.com/en/stable/deploying/gunicorn/)
- [uWSGI — Flask Documentation (3.1.x)](https://flask.palletsprojects.com/en/stable/deploying/uwsgi/)
- [How We Fixed Gunicorn Worker Errors in Our Flask App](https://glinteco.com/en/post/how-we-fixed-gunicorn-worker-errors-in-our-flask-app-a-real-troubleshooting-journey/)

### Networking and Service Discovery
- [Docker Compose Networking Mysteries Service Discovery Failures](https://www.netdata.cloud/academy/docker-compose-networking-mysteries/)
- [Networking for Docker Containers Part II: Service Discovery](https://d2iq.com/blog/networking-docker-containers-part-ii-service-discovery-traditional-apps-microservices)
- [Docker Compose Network Mode Best Practices for Complex Microservices Architectures](http://blog.poespas.me/posts/2025/02/25/docker-compose-network-mode-best-practices-microservices/)

### Secrets Management
- [Are environment variables still safe for secrets in 2026? - Security Boulevard](https://securityboulevard.com/2025/12/are-environment-variables-still-safe-for-secrets-in-2026/)
- [Do not use secrets in environment variables and here's how to do it better](https://www.nodejs-security.com/blog/do-not-use-secrets-in-environment-variables-and-here-is-how-to-do-it-better)
- [4 Ways to Securely Store & Manage Secrets in Docker](https://blog.gitguardian.com/how-to-handle-secrets-in-docker/)
- [Managing Secrets in Docker Compose — A Developer's Guide](https://phase.dev/blog/docker-compose-secrets/)

### Logging Best Practices
- [How to Implement Docker Logging Best Practices](https://oneuptime.com/blog/post/2026-01-30-docker-logging-best-practices/view)
- [Mastering Log Management in Docker: Best Practices](https://edgedelta.com/company/blog/log-management-in-docker-best-practices)
- [Flask Logging Made Simple for Developers](https://last9.io/blog/flask-logging/)

### Restart Policies and Recovery
- [Docker Container Keeps Restarting: Complete Troubleshooting Guide & Best Practices 2026](https://copyprogramming.com/howto/docker-container-keeps-on-restarting-again-on-again)
- [Start containers automatically | Docker Docs](https://docs.docker.com/engine/containers/start-containers-automatically/)
- [Solving Docker Container Restart Loops in Production Environments](https://mindfulchase.com/explore/troubleshooting-tips/devops-tools/solving-docker-container-restart-loops-in-production-environments.html)

### Image Optimization
- [Dockerizing a Flask Application: A Multi-Stage Dockerfile Approach](https://dev.to/isaackumi/dockerizing-a-flask-application-a-multi-stage-dockerfile-approach-389a)
- [Python Docker Image: Proven Hacks for Best Builds in 2026](https://cyberpanel.net/blog/python-docker-image)
- [Stop Shipping Fat Python Docker Images: Multi-Stage Builds Explained](https://dev.to/alaxay8/stop-shipping-fat-python-docker-images-multi-stage-builds-explained-2ag1)

---
*Pitfalls research for: Shopify Multi-Supplier Platform - Production Deployment*
*Researched: 2026-02-03*
*Confidence: MEDIUM-HIGH (verified with official documentation and recent 2026 sources)*
