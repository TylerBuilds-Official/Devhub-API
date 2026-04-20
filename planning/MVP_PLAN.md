# DevHub — MVP Plan

Living document. Tracks what's shipped, what's on deck, and what's deferred.
Source of truth for "are we done yet."

---

## MVP definition

DevHub ships MVP when Tyler can:

1. See every managed project's current health at a glance
2. See infra health (UpdateSuite / DB / GitHub) separately from per-project health
3. Trigger any UpdateSuite pipeline for any project from the UI
4. Watch a triggered deploy run and see its status + logs
5. Browse the audit trail of every deploy that ran through DevHub

Everything else is post-MVP.

---

## Status legend

- ✅ Shipped and working
- 🟡 Scaffolded, needs build-out
- 🔲 Not started
- ⏸ Deferred (post-MVP by design)

---

## Backend (DevHubAPI)

### ✅ Foundation
- FastAPI app at `:8766` following UpdateSuite conventions
- `api/build/` factory, `api/routers/`, `_dataclasses/`, `_errors/`, `_models/`, `repositories/`
- `.env` loading via python-dotenv at `main.py` import
- CORS wide-open for MVP

### ✅ Database (`TOOLBOX.dev_hub`)
- `Projects` — cached registry mirror, FK target
- `Deployments` — audit trail with `DeployId` UUID PK
- `HealthHistory` — append-only probe log
- `ProjectHealthLatest` — hot cache for dashboard reads
- Indexes on `(ProjectKey, CreatedAt DESC)` and `(ProjectKey, CheckedAt DESC)`

### ✅ Registry layer
- `resources/registry.json` loaded at startup
- Per-project overrides: `health_interval_s`, `verify_tls`
- Graceful `repo: null` fallback for projects without GitHub

### ✅ Health poller
- Background asyncio task per probeable project
- Per-project `AsyncClient` with `verify` honored
- Cadence resolves project → global env → 60s default
- Writes `HealthHistory` + upserts `ProjectHealthLatest`

### ✅ Endpoints live
- `GET /health` — liveness
- `GET /projects` — list with latest health
- `GET /projects/{key}` — single + latest health
- `POST /deploys` — proxy to UpdateSuite + write audit row
- `GET /jobs` — list from `Deployments` (optional `?project_key=X` filter)
- `GET /jobs/{deploy_id}` — single job, reconciled against upstream
- `GET /jobs/{deploy_id}/log` — log buffer proxied from upstream
- `GET /system/status` — UpdateSuite/DB/GitHub reachability
- `GET /upstream/apps` — proxy to UpdateSuite's `/apps`

### ⏸ Deferred
- Auth (Azure AD 4-tier RBAC) — post-MVP
- GitHub upstream check — stubbed as "unknown"
- `HealthHistory` retention/cleanup job
- Registry hot-reload endpoint
- Deploy cancellation
- Live log tail via SSE (polled buffer works for MVP)

---

## UpdateSuite changes landed during DevHub build

### ✅ Shared step helpers
- `api/_step_utils.py` with `resolve_step()` + `step_label()`
- Imported by `apps_router` (serialization) and `deploy_runner` (execution)
- Single source of truth, no divergence

### ✅ Fixed step counter
- `current_step` is 1-indexed ("step N of total, currently executing")
- Lands at `total_steps` on success (was stuck at `0/N` before)
- `current_step_label` uses docstring first line instead of method name

---

## Frontend (dev-hub)

### ✅ Foundation
- Vite 8 + React 19 + TypeScript 6
- `@` alias + `/api` proxy to `:8766` with path rewrite
- `VITE_API_URL` fallback pattern (dev proxy vs. prod explicit URL)
- Industrial dark design system — Oswald / JetBrains Mono, `#c94a1a` accent, hairline rules, no rounded cards, faint blueprint grid
- Token-aware fetch client stubbed (ready for MSAL without refactor)

### ✅ Layer structure
- `api/` — one resource module per backend router
- `types/` — matching types per resource
- `hooks/useApi.ts` — generic fetch hook with `{ intervalMs, pauseWhenHidden }` options
- `hooks/useElapsedSeconds.ts` — live tick + formatter
- `components/global/` — Header, Sidebar, LoadingSpinner, EmptyState, StatusBadge, ConfirmDialog, RefreshButton
- `components/dashboard/` — ProjectRow, DetailPane, SystemStatusStrip
- `components/jobs/` — JobsTable (shared between JobsPage + DetailPane)
- `components/deploy/` — DeployModal state machine, Form/Running/Done views, ParamInput, LogTail
- `pages/` — DashboardPage, JobsPage, JobDetailPage
- `styles/` — global, layout, dashboard, jobs, deploy-modal, job-detail

### ✅ Dashboard
- Split-pane layout (340px project list + detail pane)
- URL-driven selection — `/projects/:projectKey` deep-links cleanly; `/` falls back to first project
- Project rows with status indicator, name, category/updatesuite meta, status word
- Selected row: accent-soft background + 2px orange left bar
- Detail pane: header, description, category/tag badges, title-block field grid, last health check, recent deploys (real data), deploy buttons
- SystemStatusStrip in page header (auto-refreshes every 60s)
- Projects list auto-refreshes every 30s, pauses when tab hidden
- Manual refresh button in page header

### ✅ Deploy flow (marquee)
- Click deploy button → modal opens in FORM state
- Param inputs dispatched by type (str/bool/int), defaults honored, required validation inline
- Submit → RUNNING state, 2s poll of `/jobs/{id}` + `/jobs/{id}/log`, step counter + progress bar + auto-scrolling log tail
- Terminal status → DONE state with full summary, total duration, tail, "Open full detail" button
- 409 conflicts show inline error strip with "View" link to in-flight deploy
- Close refetches Recent Deploys in parent

### ✅ JobsPage
- Global table of all recent deploys across projects
- Project filter dropdown (dynamically populated from `/projects`)
- Columns: When / Project / Pipeline / Status / By
- Row click → `/jobs/:id`
- Manual refresh button in header

### ✅ JobDetailPage
- Deep-linkable at `/jobs/:id`
- Hero block with big status word + elapsed (live-tick while running, frozen total when done)
- Progress section (only while running)
- Title-block summary grid: deploy id, upstream job id, project, pipeline, triggered by, started, finished, steps
- Params section if any
- Error block if failed
- Full log tail (40vh)
- Polls 2s while running, quiet when terminal
- Graceful degradation when upstream has evicted log buffer
- Manual refresh button in header

### ⏸ Deferred
- MSAL / Azure AD auth
- Dark/light mode toggle (dark-only for now)
- Doc viewer / aggregation
- Registry editor UI (edit JSON in-app)
- Health history charts (sparklines / time-series)
- Sidebar expansion (Admin/Settings/System) — only add when there's somewhere to go

---

## Shipping order — complete

All seven items in the original order are shipped:

1. ✅ Backend: `?project_key=X` filter on `GET /jobs`
2. ✅ Frontend: JobsPage
3. ✅ Frontend: Recent Deploys in DetailPane
4. ✅ Frontend: Deploy modal + flow
5. ✅ Frontend: JobDetailPage
6. ✅ Frontend: Auto-refresh on dashboard (+ RefreshButton on every page)
7. ✅ Frontend: Deep-link project detail via URL param

**MVP is feature-complete against the original definition.** Everything in "MVP definition" is now achievable end-to-end.

---

## Known loose ends (tracked, not blocking)

- DevHub self-monitoring ping is weak (DevHub pings its own `/health`). Works but redundant with the system status strip. Keep or remove `devhub_api` from registry — call later.
- `verify_tls: True` default bites every time a new HTTPS project is added with a self-signed cert. Default flip is a judgment call.
- `Deployments` table grows unbounded. Monitor, add retention later.

---

## Post-MVP backlog

Ranked by expected ROI, not committed:

1. MSAL / Azure AD auth — before any other user touches it
2. Deploy cancellation — useful when a build hangs
3. Live log tail via SSE — nicer than polling
4. GitHub integration — commits, branches, diff links per project
5. Atlas tool surface — expose DevHub endpoints to FabCore's assistant
6. Doc aggregation — `docs/` across repos, searchable
7. HealthHistory retention / cleanup job
8. Registry hot-reload endpoint (editing registry.json requires process restart today)
9. Cmd+K command palette
10. Light mode
