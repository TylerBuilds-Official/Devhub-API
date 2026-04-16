# DevHub — Service Logs Feature Plan

Branch: `feature/service-logs` (new)

---

## Context

Services running under NSSM on the Aegis VM (`10.0.0.12`) write stdout/stderr
to local log files. DevHub will be deployed to the same box at
`E:\Services\DevHub\`, so log access is just local filesystem reads — no
cross-machine transport, no auth, no new services.

Log file locations follow a consistent pattern:

```
E:\Services\{Service}\{Component}\logs\{stdout|stderr}.log
```

Confirmed paths for MVP:

- `E:\Services\ScopeAnalysis\API\logs\{stdout,stderr}.log`
- `E:\Services\ScopeAnalysis\Frontend\logs\{stdout,stderr}.log`
- `E:\Services\Fabcore\API\logs\{stdout,stderr}.log`
- `E:\Services\Fabcore\Frontend\logs\{stdout,stderr}.log`

Each service has two components (API and Frontend), each with two streams
(stdout and stderr) — four files per service.

---

## Design decisions

### 1. Project entry keeps a `logs` dict keyed by component

One project entry per service (no duplication into "FabCore API" / "FabCore
Frontend"). The `logs` field is an optional dict keyed by component name
("api", "frontend"), each value being a `{stdout, stderr}` pair of absolute
paths.

Registry example:

```json
{
  "key": "scope_analysis",
  ...
  "logs": {
    "api": {
      "stdout": "E:\\Services\\ScopeAnalysis\\API\\logs\\stdout.log",
      "stderr": "E:\\Services\\ScopeAnalysis\\API\\logs\\stderr.log"
    },
    "frontend": {
      "stdout": "E:\\Services\\ScopeAnalysis\\Frontend\\logs\\stdout.log",
      "stderr": "E:\\Services\\ScopeAnalysis\\Frontend\\logs\\stderr.log"
    }
  }
}
```

Projects without a `logs` field (desktop apps, external services) simply
don't expose the feature.

### 2. Backend endpoint

`GET /projects/{key}/logs?component={name}&stream={stdout|stderr}&tail={n}`

- Reads N lines from the tail of the configured file.
- Uses a proper reverse-seek tail implementation — never slurps the full
  file. Log files could be hundreds of MB.
- 404 if the project has no logs configured or the requested
  component/stream is absent from the registry entry.
- 200 with `{lines: []}` if the file exists but is empty.
- 502 with a clear error if the file can't be read (permissions, missing
  on disk, etc.) — these are operational problems the user needs to see.

Response shape:

```json
{
  "project_key": "scope_analysis",
  "component":   "api",
  "stream":      "stdout",
  "path":        "E:\\Services\\ScopeAnalysis\\API\\logs\\stdout.log",
  "lines":       ["...", "...", "..."],
  "truncated":   false
}
```

The `path` echo is a debugging affordance — useful when log paths drift
between registry and filesystem.

### 3. Frontend inline-first, full page deferred

**Phase 1 (this session):** inline "Logs" section in DetailPane below
Recent Deploys.

- Two toggles stacked at the top of the section:
  - Component: API | Frontend (if multiple components exist)
  - Stream:    stdout | stderr
- Log tail view: ~200 lines, auto-scroll to bottom on refresh
- Auto-refresh every 5s, pauses when tab hidden (useApi already has this)
- Manual refresh icon in the section header

**Phase 2 (next session):** full `LogsPage` at `/projects/:key/logs`
with bigger viewport, tail size selector (100/500/1000/2000), and a
copy-to-clipboard button. Deep-linkable from the inline section's
"Open full logs" link.

### 4. Visual treatment

- Log tail reuses the `.deploy-log-tail` base style (monospace, dark
  bg, auto-scroll). Already battle-tested from the deploy modal.
- Slightly darker background than the deploy tail — closer to actual
  black (`#0a0a0a`) to feel terminal-native and separate the viewport
  from the surrounding DetailPane.
- Line numbers in `--text-dim` along the left edge.
- No severity highlighting in Phase 1. Add in Phase 2 if time allows
  (regex-match `ERROR`/`WARN`, colorize the line).

---

## Build order

### Phase 1 — Backend (~20 min)

1. **Registry schema addition.**
   - Update `ProjectEntry` dataclass with `logs: dict | None = None`.
   - Update `registry.py` loader to read it.
   - Update `ProjectInfo` Pydantic model + `_serialize` in
     `projects_router.py` to expose it.
   - Update `registry.json` with the confirmed paths for FabCore and
     Scope (API + Frontend).

2. **Log reading utility.** New module `api/log_reader.py`:
   - `tail_file(path: str, n: int) -> list[str]` — efficient reverse-read.
   - Handles UTF-8 with `errors="replace"` (log files can have mojibake).
   - Handles missing file (raise a typed exception).
   - Handles empty file (returns empty list).

3. **Logs Pydantic models.** `api/_models/log_models.py`:
   - `LogsResponse` with project_key, component, stream, path, lines.

4. **Logs router.** `api/routers/logs_router.py`:
   - `GET /projects/{key}/logs` with query params `component`, `stream`,
     `tail` (validate `tail` with `Query(200, ge=1, le=5000)`).
   - Reads from registry, validates component/stream exists, calls
     `log_reader.tail_file`, returns `LogsResponse`.
   - Maps errors to appropriate HTTP codes.
   - Add to `routes.py`.

### Phase 2 — Frontend inline section (~20 min)

1. **API client + types.** `src/api/logs.ts`, `src/types/log.ts`.

2. **New component:** `src/components/logs/ServiceLogs.tsx`.
   - Props: `project: ProjectInfo`.
   - Renders nothing if `project.logs` is absent.
   - Component toggle (if >1 component), stream toggle (stdout/stderr).
   - useApi with 5s interval for the log fetch.
   - Reuses `DeployLogTail` for rendering.

3. **Wire into DetailPane.** New section below "Recent deploys" that
   renders `<ServiceLogs project={project} />`.

4. **CSS polish in `deploy-modal.css`** or a new `logs.css` for the
   toggle buttons (borrowing the industrial segmented-button pattern).

---

## Registry update (Tyler to verify exact paths)

**FabCore:**
```
E:\Services\Fabcore\API\logs\stdout.log
E:\Services\Fabcore\API\logs\stderr.log
E:\Services\Fabcore\Frontend\logs\stdout.log
E:\Services\Fabcore\Frontend\logs\stderr.log
```

**Scope Analysis:**
```
E:\Services\ScopeAnalysis\API\logs\stdout.log
E:\Services\ScopeAnalysis\API\logs\stderr.log
E:\Services\ScopeAnalysis\Frontend\logs\stdout.log
E:\Services\ScopeAnalysis\Frontend\logs\stderr.log
```

Once DevHub is deployed: its own logs at
`E:\Services\DevHub\API\logs\` and `E:\Services\DevHub\Frontend\logs\`
can be added to the `devhub_api` registry entry. Dogfooding.

UpdateSuite stays off this feature — it runs on Tyler's workstation,
not on Aegis. DevHub won't have a path to those logs until UpdateSuite
either moves or gets a proper log endpoint. Track in loose ends.

---

## Open items for after Phase 1 + 2 ship

- **Log paths for UpdateSuite.** Either move UpdateSuite to Aegis at
  some point, or add an HTTP log endpoint to it and have DevHub fetch
  via HTTP for that one service.
- **Full LogsPage.** Bigger viewport, tail size selector, copy, severity
  coloring, maybe search.
- **Log rotation awareness.** If NSSM rotates `stdout.log` to
  `stdout.old.log`, current tail won't reach into the rotated file.
  Probably acceptable for MVP.
- **Line rate limiting.** If a service goes berserk and writes 10,000
  lines/sec, tailing the last 200 is fine but the UI may feel busy.
  Not a real problem yet.

---

## Non-goals

- No live streaming. Polled tail at 5s is plenty for "watch what's
  happening" and avoids the SSE/websocket complexity.
- No log writing from DevHub. This is a read-only window.
- No log archiving / indexing / search. That's a log aggregator's job
  (Loki, Elasticsearch), not DevHub's. Keep scope honest.
