# DevHub — Auth Plan

Living document. First post-MVP effort. Auth-gates DevHubAPI (`:8766`) and dev-hub (`:5174`). UpdateSuite (`:8765`) stays trusted — localhost-only, Tyler's firewall handles perimeter.

**Status:** Shipped end-to-end. Signed-in admin flow verified against the running stack on 2026-04-17.

---

## Scope

**In:**
- MSAL.js login on dev-hub (interactive, reusing the JobScan app registration)
- Bearer-token attach on every DevHubAPI request
- DevHubAPI validates JWT (signature, issuer, tenant, expiry)
- Two-tier RBAC: `viewer` | `admin`, sourced from `TOOLBOX.dev_hub.UserRoles`
- Per-route policy enforcement (GET = viewer+, POST/mutations = admin)

**Out:**
- Custom API scope / "Expose an API" on the app reg (using Graph audience)
- AAD App Roles (using SQL table instead, runtime-mutable)
- UpdateSuite auth (stays trusted, localhost-bound)
- Token refresh UI — MSAL.js handles silent renewal under the hood
- 4-tier RBAC from original MVP plan (collapsed to 2-tier)

---

## Status legend

- ✅ Shipped and working
- 🟡 Scaffolded, needs build-out
- ✅ Not started

---

## Identity

- **Tenant ID:** `99857259-7d6a-47fb-a35b-7f6004c4965d`
- **Client ID (app reg):** `79633382-952d-4e11-bd6d-6f047bf5732b` (shared with JobScan desktop)
- **Authority:** `https://login.microsoftonline.com/{TENANT_ID}`
- **Scopes requested:** `User.Read` (Graph — gives us email/displayName)
- **SPA redirect URI:** `http://localhost:5174` (already configured in Azure AD)

**Token audience note:** the frontend sends the **ID token**, not the Graph access token. Graph access tokens use a hashed-nonce signing scheme that standard JWT libraries cannot verify — Microsoft explicitly documents that Graph access tokens "should not be inspected by the service for which they were issued." ID tokens from the same sign-in flow are standard RS256 JWTs signed with the tenant's published JWKS and carry the same identity claims (`preferred_username`, `upn`, `name`) we need. Audience on the ID token is our `AAD_CLIENT_ID`.

---

## Architecture

```
[dev-hub SPA]
    │
    │  1. MSAL.js loginPopup() → interactive AAD login
    │  2. acquireTokenSilent({ scopes: ['User.Read'] }) → bearer token
    │  3. fetch('/api/...', { Authorization: `Bearer ${token}` })
    ▼
[DevHubAPI :8766]
    │
    │  4. Dependency: decode + validate JWT (cache JWKS)
    │  5. Extract email from `preferred_username` / `upn`
    │  6. Lookup role in UserRoles table
    │  7. Route-level policy check (viewer / admin)
    ▼
[UpdateSuite :8765]  ← unchanged, trusted
```

---

## Backend (DevHubAPI)

### ✅ Dependencies
- `msal` — not needed server-side (validation only)
- `PyJWT[crypto]` — JWT decode + signature verification
- `httpx` — already present, fetch JWKS from Microsoft
- `cachetools` — JWKS TTL cache (avoid hitting login.microsoftonline.com every request)

### ✅ DB: `TOOLBOX.dev_hub.UserRoles`

```sql
CREATE TABLE dev_hub.UserRoles (
    Email        NVARCHAR(256) NOT NULL PRIMARY KEY,
    Role         NVARCHAR(32)  NOT NULL CHECK (Role IN ('viewer', 'admin')),
    CreatedAt    DATETIME2     NOT NULL DEFAULT SYSUTCDATETIME(),
    CreatedBy    NVARCHAR(256) NULL,
    Notes        NVARCHAR(512) NULL
);
```

Seed Tyler as the first admin:

```sql
INSERT INTO dev_hub.UserRoles (Email, Role, CreatedBy, Notes)
VALUES ('tylere@metalsfab.com', 'admin', 'bootstrap', 'Initial admin seed');
```

### ✅ Auth module — `api/auth/`

Structure:

```
api/auth/
├── __init__.py
├── jwks.py          # JWKS fetch + cache (TTL ~1h)
├── verifier.py      # decode_and_validate(token) -> dict claims
├── roles.py         # get_role_for_email(email) -> 'viewer' | 'admin' | None
├── dependencies.py  # FastAPI dependencies: current_user, require_admin
└── _models.py       # AuthenticatedUser dataclass
```

**Dependencies exposed:**
- `current_user: AuthenticatedUser = Depends(get_current_user)` — any signed-in role
- `admin: AuthenticatedUser = Depends(require_admin)` — 403 if not admin

`AuthenticatedUser`:
```python
@dataclass(frozen=True)
class AuthenticatedUser:
    email: str
    display_name: str
    role: Literal['viewer', 'admin']
    claims: dict  # raw token claims, for debugging/audit
```

### ✅ Route-level policy

| Route | Requires |
|---|---|
| `GET /health` | **public** (liveness probe) |
| `GET /projects`, `/projects/{key}` | `current_user` |
| `GET /jobs`, `/jobs/{id}`, `/jobs/{id}/log` | `current_user` |
| `GET /system/status` | `current_user` |
| `GET /upstream/apps` | `current_user` |
| `POST /deploys` | `require_admin` |

Audit trail: `POST /deploys` already records `triggered_by` — change from env-default to `current_user.email`.

### ✅ Config (`.env`)

Add to `.env.example`:
```
AAD_TENANT_ID=99857259-7d6a-47fb-a35b-7f6004c4965d
AAD_CLIENT_ID=79633382-952d-4e11-bd6d-6f047bf5732b
AAD_AUDIENCE=79633382-952d-4e11-bd6d-6f047bf5732b   # our client id — ID tokens have aud = client_id
AAD_JWKS_URL=https://login.microsoftonline.com/99857259-7d6a-47fb-a35b-7f6004c4965d/discovery/v2.0/keys
```

### ✅ CORS

Already wide-open for MVP. Tighten to `http://localhost:5174` (dev) + prod origin once chosen. Add `Authorization` to `allow_headers`.

---

## Frontend (dev-hub)

### ✅ Dependencies
```
@azure/msal-browser
@azure/msal-react
```

### ✅ MSAL config — `src/auth/msalConfig.ts`

```ts
export const msalConfig = {
  auth: {
    clientId:    import.meta.env.VITE_AAD_CLIENT_ID,
    authority:   `https://login.microsoftonline.com/${import.meta.env.VITE_AAD_TENANT_ID}`,
    redirectUri: window.location.origin,
  },
  cache: {
    cacheLocation: 'sessionStorage',  // cleared when tab closes; 'localStorage' if persistence wanted
    storeAuthStateInCookie: false,
  },
}

export const loginRequest = {
  scopes: ['User.Read'],
}
```

### ✅ App wrapping — `src/main.tsx`

```tsx
<MsalProvider instance={pca}>
  <AuthGate>
    <App />
  </AuthGate>
</MsalProvider>
```

### ✅ `<AuthGate>` — `src/auth/AuthGate.tsx`

- If no account → render sign-in screen with single "Sign in with Microsoft" button
- If account → render children
- Handle `InteractionRequiredAuthError` → prompt popup

### ✅ Token-aware fetch — update existing `src/api/client.ts` (already stubbed per MVP plan)

```ts
async function getAccessToken(): Promise<string> {
  const account = pca.getAllAccounts()[0]
  const result = await pca.acquireTokenSilent({ ...loginRequest, account })
  return result.accessToken
}
```

Attach as `Authorization: Bearer <token>` on every request. On `401`, trigger `acquireTokenPopup` once; on second failure, surface sign-in prompt.

### ✅ User chip in header — `src/components/global/Header.tsx`

- Show display name + avatar (optional — can defer photo, just name/email for v1)
- Click → dropdown with "Sign out"
- Sign out → `pca.logoutPopup()`

### ✅ 403 handling

Non-admin hitting the deploy button → API returns 403 → modal shows "You don't have permission to deploy. Contact an admin." Disable deploy buttons up-front if role is known (fetch role via new `GET /me` endpoint on DevHubAPI).

### ✅ Config (`.env.example`)
```
VITE_AAD_TENANT_ID=99857259-7d6a-47fb-a35b-7f6004c4965d
VITE_AAD_CLIENT_ID=79633382-952d-4e11-bd6d-6f047bf5732b
```

---

## New endpoint: `GET /me`

Useful for the frontend to know its own role without round-tripping every action.

```json
{
  "email": "tylere@metalsfab.com",
  "display_name": "Tyler E",
  "role": "admin"
}
```

Lets the dashboard hide/disable admin-only UI upfront (deploy buttons, etc.).

---

## UpdateSuite — unchanged

UpdateSuite (`:8765`) runs on Tyler's workstation, localhost-bound, firewall-controlled. DevHubAPI still proxies to it as a trusted client. No auth changes there.

If UpdateSuite ever gets exposed beyond localhost, this plan gets a second chapter: pass user context through from DevHubAPI so audit trail preserves identity end-to-end.

---

## Shipping order

1. ✅ DB migration: `UserRoles` table + Tyler admin seed
2. ✅ Backend: JWKS fetcher + JWT verifier (unit-testable in isolation)
3. ✅ Backend: `api/auth/` module + FastAPI dependencies
4. ✅ Backend: wire dependencies onto routes per policy table above
5. ✅ Backend: `GET /me` endpoint
6. ✅ Frontend: install MSAL, wire `MsalProvider`, build `AuthGate` sign-in screen
7. ✅ Frontend: attach bearer in `api/client.ts`, handle 401 silent-retry
8. ✅ Frontend: user chip in header + sign-out
9. ✅ Frontend: `/me` fetch at boot, disable admin UI for viewers
10. ✅ Frontend: 403 error surfaces on admin-only action attempts
11. ✅ Tighten CORS to explicit origins

---

## Known gotchas

- **ID token vs Graph access token** — the frontend sends the ID token, not the Graph access token. Graph access tokens use a hashed-nonce signing scheme that standard JWT libraries cannot verify; they are not intended to be validated by third parties. ID tokens are standard RS256 JWTs with `aud = client_id` and are what the verifier checks.
- **Signature algorithm** — tokens are RS256, validate via JWKS public keys. Never accept `alg: none`.
- **Clock skew** — allow ±60s on `exp` / `nbf` validation.
- **JWKS cache** — cache keys for ~1 hour. Refresh on signature-mismatch (key rotation).
- **Email source** — prefer `preferred_username`, fall back to `upn`. Lowercase for lookup.
- **Session persistence** — `sessionStorage` means Tyler re-signs each new tab / browser restart. Flip to `localStorage` if annoying; tradeoff is tokens persist on disk.
- **Interactive-only acquisition** — silent refresh requires a cached account; first-time users always hit the popup. This is expected.
- **MSAL.js popup blockers** — Chrome/Edge sometimes block; MSAL falls back to redirect flow. Test both.

---

## Open questions (tracked)

- User photo from Graph in the header chip — nice to have, deferrable.
- Admin UI for managing `UserRoles` (add/remove users from within DevHub) — post-this-plan. For now, Tyler edits the table directly or via a SQL script.
- What happens when a user with no `UserRoles` row signs in successfully via AAD? Recommend: 403 with "Your account is not authorized for DevHub. Contact an admin." Do not auto-seed.

---

## Post-auth backlog (unchanged from MVP plan's post-MVP list)

2. Deploy cancellation
3. Live log tail via SSE
4. GitHub integration
5. Atlas tool surface
6. Doc aggregation
7. HealthHistory retention
8. Registry hot-reload
9. Cmd+K palette
10. Light mode
