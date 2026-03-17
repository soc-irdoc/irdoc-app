# Troubleshooting

Common errors encountered during installation and first run, with solutions.

---

## Docker / First Run

---

### Variables defaulting to blank string (`DB_PASSWORD`, `SECRET_KEY`, etc.)

**Full error example:**
```
level=warning msg="The \"DB_PASSWORD\" variable is not set. Defaulting to a blank string."
level=warning msg="The \"SECRET_KEY\" variable is not set. Defaulting to a blank string."
```

**Cause:**
Docker Compose cannot find the `.env` file. This happens when you run `docker compose up` from the `docker/` subdirectory but the `.env` file is at the project root (`incident-response-platform/.env`). Docker Compose looks for `.env` relative to the `docker-compose.yml` file location, but the compose file uses `env_file: ../.env` which points one level up.

The most common cause is simply that `.env` has not been created yet (you only have `.env.example`).

**Fix:**
The `.env` file must live inside `docker/` — the same directory as `docker-compose.yml`. Docker Compose reads `.env` from the **current working directory** for YAML variable substitution, which is `docker/` when you run from there.

```bash
# From the project root:
cp .env.example docker/.env
# Edit docker/.env and set DB_PASSWORD, REDIS_PASSWORD, SECRET_KEY
```

Then run Docker Compose from the `docker/` directory:
```bash
cd docker
docker compose up
```

**Why does this happen?**
Docker Compose has two separate env-loading mechanisms:
1. **YAML variable substitution** (`${DB_PASSWORD}` in compose YAML) — reads `.env` from the *working directory* where you run the command.
2. **`env_file:` directive** — injects variables into containers at runtime, path relative to the compose file.

These are resolved at different times. Running from `docker/` means substitution looks for `docker/.env`, regardless of what `env_file:` points to.

---

### `no matching manifest for windows(...)/amd64 in the manifest list entries`

**Full error example:**
```
! Image redis:7-alpine     Interrupted
no matching manifest for windows(10.0.26200)/amd64 in the manifest list entries
```

**Cause:**
Docker Desktop is running in **Windows containers mode**. All IRDoc images (`postgres:16-alpine`, `redis:7-alpine`, `python:3.12-slim`, `node:20-alpine`, `nginx:alpine`) are Linux images. They cannot run in Windows container mode.

**Affected versions confirmed:**
- Docker Desktop 29.2.1, Docker Compose v5.1.0, Windows 11 Pro 26200

**Fix:**
Switch Docker Desktop to Linux containers mode:

1. Find the Docker whale icon in the Windows system tray (bottom-right taskbar, may be in the hidden icons `^` menu)
2. **Right-click** the whale icon
3. Click **"Switch to Linux containers..."**
4. Wait ~10–15 seconds for Docker to restart
5. Right-click again — you should now see **"Switch to Windows containers..."** (confirming you are currently on Linux mode)
6. Re-run `docker compose up`

**Why this happens:**
Docker Desktop on Windows supports two modes. Linux containers mode (the default on a fresh install) runs a lightweight Linux VM and is required for almost all Docker Hub images. Windows containers mode runs Windows-native containers and is rarely needed. It can get switched accidentally.

**Prevention:**
Docker Desktop remembers the last mode. Once switched to Linux containers, it stays there across restarts.

---

## Backend

---

### `E: Package 'libgdk-pixbuf2.0-0' has no installation candidate`

**Full error example:**
```
17.81 Package libgdk-pixbuf2.0-0 is not available, but is referred to by another package.
17.81 However the following packages replace it:
17.81   libgdk-pixbuf-xlib-2.0-0
E: Package 'libgdk-pixbuf2.0-0' has no installation candidate
target worker: failed to solve: process "/bin/sh -c apt-get update && apt-get install ..."
```

**Cause:**
The untagged `python:3.12-slim` image silently moved from Debian Bookworm (12) to Debian Trixie (13). In Trixie the `libgdk-pixbuf2.0-0` package was split and renamed — the old name no longer exists. WeasyPrint (used for PDF report generation) depends on this library.

**Fix:**
Pin the base image to the Bookworm variant in [backend/Dockerfile](../../backend/Dockerfile):

```dockerfile
# Before:
FROM python:3.12-slim

# After:
FROM python:3.12-slim-bookworm
```

**Why Bookworm and not Trixie?**
Debian Bookworm (12) is the current stable release and is what all major Python Docker images were built against. Trixie is the next testing branch — package names and availability are still in flux. Pinning to `-bookworm` gives a stable, predictable base and avoids this class of breakage entirely. The same fix applies to any `*-slim` image that silently upgrades its Debian base.

---

## Frontend

---

### `npm ci` fails — `can only install with an existing package-lock.json`

**Full error example:**
```
#18 1.775 npm error code EUSAGE
#18 1.775 npm error The `npm ci` command can only install with an existing package-lock.json or
#18 1.775 npm error npm-shrinkwrap.json with lockfileVersion >= 1.
target frontend: failed to solve: process "/bin/sh -c npm ci" did not complete successfully: exit code: 1
```

**Cause:**
`npm ci` is a strict, reproducible install that requires a committed `package-lock.json`. When the repo has never had `npm install` run locally (and the lockfile was never generated or committed), the Docker build fails immediately.

**Fix:**
Change `npm ci` to `npm install` in [frontend/Dockerfile](../../frontend/Dockerfile):

```dockerfile
# Before (line 4):
RUN npm ci

# After:
RUN npm install
```

**Why not just run `npm install` locally to generate the lockfile?**
That requires Node.js installed on the host. Since the project is Docker-only for local dev, fixing the Dockerfile is the simpler path.

**Production note — do this before going to production:**
`npm install` works but is not reproducible across builds (different dates may resolve different patch versions). Before publishing and deploying to production:

1. Generate the lockfile. If you don't have Node installed locally, use a temporary container:
   ```bash
   docker run --rm -v /path/to/incident-response-platform/frontend:/app -w /app node:20-alpine npm install
   ```
2. Commit the generated `frontend/package-lock.json` to the repository.
3. Revert the Dockerfile back to `npm ci`:
   ```dockerfile
   RUN npm ci
   ```

Once the lockfile is committed, `npm ci` is faster, reproducible, and will catch accidental `package.json` / lockfile drift in CI.

---

---

### Frontend build fails with TypeScript errors (`tsc && vite build`)

**Full error example:**
```
#20 [frontend builder 6/6] RUN npm run build
src/components/graph/InvestigationGraph.tsx(155,58): error TS2345: ...
src/components/reports/GenerateReportModal.tsx(2,8): error TS2613: Module has no default export
target frontend: failed to solve: process "/bin/sh -c npm run build" did not complete successfully: exit code: 1
```

**Cause:**
TypeScript strict-mode errors that were not caught during development (files were authored without a real `tsc` invocation). The Docker build runs `tsc && vite build` which enforces strict type checking.

**Errors fixed (first run):**

| File | Error | Fix |
|---|---|---|
| `GenerateReportModal.tsx`, `SyncPolicySection.tsx` | Modal has no default export | Changed to named import `import { Modal } from` |
| `useReportTemplates.ts`, `useReports.ts`, `useSyncPolicies.ts` | `addToast` receives object but expects `(message, type)` | Changed call signature to match `addToast(message, type)` |
| `src/types/graph.ts` | `GraphNodeData` missing index signature | Added `[key: string]: unknown` to satisfy React Flow's `Record<string, unknown>` constraint |
| `InvestigationGraph.tsx` | `GraphEdge.label?: string` vs React Flow `Edge.label?: ReactNode` | Added explicit generics + `as Node[]` / `as Edge[]` casts |
| `src/components/common/Modal.tsx` | `maxWidth` prop not in `ModalProps` | Added `maxWidth?: number` to `ModalProps` |
| `src/components/ioc/IOCPage.tsx` | Multiple `unknown` not assignable to `ReactNode` | Added explicit `IOC` typing, `!!` guards, proper index key types |

**Prevention for future development:**
Run `tsc --noEmit` locally before committing to catch type errors before they reach the Docker build:
```bash
cd frontend && npm run type-check
```

---

## Backend Runtime

---

### `AttributeError: module 'app' has no attribute 'include_router'`

**Full error example:**
```
AttributeError: module 'app' has no attribute 'include_router'
  File "/app/app/main.py", line 145, in <module>
      app.include_router(auth.router, prefix=API_PREFIX)
      ^^^^^^^^^^^^^^^^^^
AttributeError: module 'app' has no attribute 'include_router'
```

**Cause:**
`backend/app/main.py` contains `import app.plugins` (to load integration plugins on startup). This import rebinds the name `app` in the module's namespace to the `app/` Python package, shadowing the `FastAPI()` instance that was previously assigned to the same name.

**Fix:**
Rename the FastAPI instance variable from `app` to `application` throughout `backend/app/main.py`, and update the uvicorn target in `backend/entrypoint.sh` from `app.main:app` to `app.main:application`. This is already applied in the codebase.

---

## Database / Migrations

*(No entries yet — add as discovered)*

---

## Celery / Workers

*(No entries yet — add as discovered)*

---

*This file is updated as new issues are discovered. If you encounter an error not listed here, please open a GitHub issue.*
