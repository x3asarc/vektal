# Next Tasks - Frontend Deployment Debug Session

## Goal
Deploy the new "Bureaucratic Brutalism" UI (Matrix Green theme) to production at app.vektal.systems

## Current Status: PAUSED
**Last Updated:** 2026-03-05 00:15 UTC

### What We Tried
1. Run Next.js dev server locally to preview new UI
2. Hit infinite compilation issue - pages never loaded
3. Attempted deployment to Hetzner server via Dokploy

### Root Causes Discovered

#### Issue 1: Zombie Next.js Process (FIXED)
- **Problem:** Another Next.js dev server was running and holding `.next/dev/lock`
- **Error:** `Unable to acquire lock at .next/dev/lock`
- **Solution:**
  - Found process: `netstat -ano | findstr :3000` → PID 13136
  - Killed: `taskkill //PID 13136 //F`
  - Removed lock: `rm -f frontend/.next/dev/lock`

#### Issue 2: Original Dashboard Page Causes Infinite Compilation (PARTIALLY FIXED)
- **Problem:** `frontend/src/app/(app)/dashboard/page.tsx` never finishes compiling
- **Symptom:** Server shows `○ Compiling /dashboard ...` forever (no error message)
- **Workaround:** Created simplified dashboard at same path
- **Original backed up to:** `frontend/src/app/(app)/dashboard/page.tsx.backup`

#### Issue 3: Simplified Dashboard Returns 404 (CURRENT)
- **Problem:** Simplified dashboard compiles (71s) but returns 404
- **Likely Cause:** Route group `(app)` folder or layout configuration issue
- **Files involved:**
  - `frontend/src/app/(app)/dashboard/page.tsx` (new simplified version)
  - `frontend/src/app/(app)/layout.tsx`
  - `frontend/src/app/layout.tsx`

### Current Dev Server State
- **Running:** Yes (task ID: b4d838b)
- **Port:** 3000
- **URL:** http://localhost:3000
- **Status:** Ready but /dashboard returns 404
- **Test page works:** http://localhost:3000/test (created as simple test)

### Hetzner Server Deployment (BLOCKED)
- **Server IP:** 89.167.74.58
- **Project Path:** /opt/vektal
- **Issue:** Docker containers can't reach internet (apt-get fails)
- **Symptoms:**
  - Host can reach internet (wget works)
  - Containers timeout on DNS resolution
  - Docker daemon configured with DNS 8.8.8.8
- **Frontend container not running:** Port conflict with Dokploy (both want 3000)

### Dokploy Setup (INCOMPLETE)
- **URL:** http://89.167.74.58:3000
- **Status:** Running but GitHub OAuth redirect fails
- **Alternative:** Use Personal Access Token instead of OAuth
- **Attempted:** Pasted docker-compose.yml directly → failed (missing Dockerfiles)
- **Need:** Connect to GitHub repo properly to pull full source

---

## Next Steps to Complete

### Option A: Fix Local Dev Server (Recommended - Fastest)
1. **Fix 404 issue:**
   - Check if `(app)` route group is configured correctly
   - Verify `frontend/src/app/(app)/layout.tsx` exists and is valid
   - Try moving dashboard directly to `frontend/src/app/dashboard/page.tsx` (no route group)

2. **Restore original dashboard:**
   - Once route works, investigate why original page causes infinite compilation
   - Possible culprits:
     - `@/features/resolution/components/DryRunReview` import
     - Circular dependency in feature modules
     - Turbopack-specific bug with CSS modules
   - Use original: `mv frontend/src/app/(app)/dashboard/page.tsx.backup frontend/src/app/(app)/dashboard/page.tsx`

3. **Deploy to production:**
   - Once working locally, build production: `npm run build`
   - Deploy via Dokploy or manual docker-compose

### Option B: Fix Hetzner Docker Networking
1. **Diagnose container networking:**
   ```bash
   # SSH to server
   ssh root@89.167.74.58

   # Check if UFW is blocking Docker
   iptables -t nat -L POSTROUTING -v

   # Try adding UFW route rules
   ufw route allow from 172.17.0.0/16
   ufw route allow from 172.19.0.0/16
   ufw reload
   ```

2. **Alternative:** Use pre-built images instead of building on server

### Option C: Fix Dokploy GitHub Integration
1. **Create GitHub Personal Access Token:**
   - https://github.com/settings/tokens/new
   - Scope: `repo` + `workflow`

2. **Add to Dokploy:**
   - Settings → Git Providers → Add Provider
   - Type: GitHub (Token)
   - Paste token

3. **Create Application:**
   - Project: vektal
   - Source: Git Repository
   - URL: https://github.com/x3asarc/vektal
   - Branch: master

---

## Files Created/Modified This Session

### Created
- `frontend/src/app/test/page.tsx` - Simple test page to verify Next.js works
- `frontend/src/app/(app)/dashboard/page.tsx` - Simplified dashboard (overwrote original)
- `scripts/deploy_via_hetzner_api.py` - Hetzner API deployment script
- `scripts/deploy_to_hetzner.sh` - SSH deployment script
- `scripts/deploy_frontend.sh` - Local Docker build script
- `.github/workflows/deploy-frontend.yml` - GitHub Actions workflow
- `Dockerfile.frontend` - Production build Dockerfile for frontend

### Modified
- `frontend/next.config.ts` - Added `output: 'standalone'` for Docker

### Backed Up
- `frontend/src/app/(app)/dashboard/page.tsx.backup` - Original dashboard with full features

---

## Environment Variables Needed (from /opt/vektal/.env)

Key vars for production:
```bash
APP_URL=https://app.vektal.systems
FRONTEND_URL=https://app.vektal.systems
NODE_ENV=production
```

Full .env file available on server at `/opt/vektal/.env`

---

## Useful Commands

### Local Dev
```bash
# Start dev server
cd frontend && npm run dev

# Check what's using port 3000
netstat -ano | findstr :3000

# Kill process by PID
taskkill //PID <pid> //F

# Clear build cache
rm -rf frontend/.next
```

### Hetzner Server
```bash
# SSH
ssh root@89.167.74.58

# Check containers
docker ps
docker compose -f /opt/vektal/docker-compose.yml ps

# View logs
docker logs <container_name>

# Rebuild frontend only
cd /opt/vektal
docker compose up -d frontend --build
```

---

## Key Learnings

1. **Always check for zombie processes** before debugging compilation issues
2. **Lock files** in `.next/dev/lock` can block new dev server starts
3. **Turbopack** (Next.js 16 default) can have different bugs than webpack
4. **Docker container networking** on Hetzner needs special firewall rules
5. **Dokploy GitHub OAuth** doesn't work well with IP-only access (use PAT instead)
6. **Route groups** like `(app)` can cause unexpected 404s if layout is misconfigured

---

## When Resuming This Task

1. Read this file completely
2. Check if dev server is still running: `curl http://localhost:3000/test`
3. If not, restart: `cd frontend && npm run dev`
4. Choose Option A, B, or C above based on priority
5. Test thoroughly before deploying to production

---

## Contact/Resources
- **Frontend code:** `frontend/src/app/(app)/dashboard/`
- **Deployment scripts:** `scripts/deploy_*.sh`
- **Server:** 89.167.74.58 (Hetzner)
- **Dokploy:** http://89.167.74.58:3000
- **Production URL:** https://app.vektal.systems
