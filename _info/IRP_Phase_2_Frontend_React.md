# IRP Phase 2 — Frontend: React Application

> **Status:** Planning  
> **Depends on:** Phase 1 API running and tested  
> **Estimated effort:** 4–5 weeks (1–2 frontend developers)  
> **Goal:** A pixel-faithful React port of the HTML prototype, wired to the real backend API, with auth, real-time updates, and full CRUD on all core sections. External reference display, API key management UI, and storage config UI are included here as they are needed from day one.

---

## 1. Objectives

By the end of Phase 2:
- The HTML prototype is fully reimplemented as a React + TypeScript application
- All UI interactions hit the real API — no mock data anywhere
- Auth is implemented (login, protected routes, JWT refresh)
- External references (SDP, ManageEngine, etc.) are displayed in the incident header
- API key management UI is in the admin/settings area
- Real-time timeline updates work via WebSocket
- All core sections functional: Timeline, IOCs, Summary, Tasks, Reports (UI shell), Integrations (UI shell), Settings
- The app is containerized and served by Nginx

---

## 2. Design System Migration

The prototype uses CSS custom properties and two Google Fonts (Syne + JetBrains Mono). These are preserved exactly in the React application.

### 2.1 Tailwind Configuration

```js
// tailwind.config.js
export default {
  content: ['./src/**/*.{ts,tsx}'],
  darkMode: ['attribute', '[data-theme="dark"]'],
  theme: {
    extend: {
      fontFamily: {
        display: ['Syne', 'sans-serif'],
        mono:    ['JetBrains Mono', 'monospace'],
      },
      colors: {
        'bg-base':       'var(--bg-base)',
        'bg-surface':    'var(--bg-surface)',
        'bg-elevated':   'var(--bg-elevated)',
        'bg-card':       'var(--bg-card)',
        'accent':        'var(--accent)',
        'status-red':    'var(--red)',
        'status-green':  'var(--green)',
        'status-yellow': 'var(--yellow)',
        'status-blue':   'var(--blue)',
        'status-purple': 'var(--purple)',
      },
    }
  }
}
```

The exact CSS variable blocks from the prototype (dark + light theme) live in `src/styles/global.css`. Theme switching is `data-theme` on `<html>` — identical to the prototype.

---

## 3. Application Structure

```
src/
├── components/
│   ├── layout/
│   │   ├── AppShell.tsx              # Main layout: nav + content + tasks panel
│   │   ├── LeftNav.tsx               # Icon nav with tooltips
│   │   ├── TopBar.tsx                # Incident badge, title, external ref, actions
│   │   └── TasksPanel.tsx            # Right panel — always visible
│   │
│   ├── timeline/
│   │   ├── TimelinePage.tsx
│   │   ├── AddEntryForm.tsx
│   │   ├── AttachmentZone.tsx        # Drag/drop + paste screenshot
│   │   ├── AttachmentThumb.tsx
│   │   ├── TimelineList.tsx
│   │   ├── TimelineEntry.tsx
│   │   └── TimelineFilters.tsx
│   │
│   ├── ioc/
│   │   ├── IOCPage.tsx
│   │   ├── IOCTable.tsx
│   │   ├── IOCRow.tsx
│   │   ├── IOCAddForm.tsx
│   │   └── ConfidenceBar.tsx
│   │
│   ├── summary/
│   │   ├── SummaryPage.tsx
│   │   ├── StatCard.tsx
│   │   └── EditableSection.tsx
│   │
│   ├── reports/
│   │   ├── ReportPage.tsx            # Shell only in Phase 2 — functional in Phase 3
│   │   └── ReportCard.tsx
│   │
│   ├── integrations/
│   │   ├── IntegrationsPage.tsx      # Shell only in Phase 2 — functional in Phase 4
│   │   └── IntegrationCard.tsx
│   │
│   ├── settings/
│   │   ├── SettingsPage.tsx
│   │   ├── ProfileSection.tsx
│   │   ├── APIKeysSection.tsx        # Create, list, revoke API keys
│   │   └── ToggleRow.tsx
│   │
│   └── common/
│       ├── Badge.tsx
│       ├── Button.tsx
│       ├── Toast.tsx
│       ├── Modal.tsx
│       ├── PremiumGate.tsx           # Lock overlay for premium features
│       ├── ToggleSwitch.tsx
│       ├── EmptyState.tsx
│       ├── LoadingSpinner.tsx
│       ├── ExternalRefBadge.tsx      # Displays SDP/Jira/ME ref with link
│       └── ProgressBar.tsx
│
├── pages/
│   ├── LoginPage.tsx
│   ├── IncidentListPage.tsx          # Dashboard — list of all incidents
│   └── IncidentWorkspacePage.tsx     # Main workspace — routes to sub-sections
│
├── hooks/
│   ├── useIncident.ts
│   ├── useTimeline.ts
│   ├── useIOCs.ts
│   ├── useTasks.ts
│   ├── useAttachments.ts
│   ├── useFeatureFlags.ts
│   ├── useAPIKeys.ts
│   └── useAuth.ts
│
├── stores/
│   ├── authStore.ts                  # Current user, access token (in-memory)
│   ├── themeStore.ts                 # Dark/light (persisted to localStorage)
│   └── uiStore.ts                   # Active section, modal state, toast queue
│
├── lib/
│   ├── apiClient.ts                  # Axios + token injection + refresh interceptor
│   ├── websocket.ts                  # Socket.io client
│   ├── iocDetector.ts               # Client-side IOC auto-detect (mirrors backend regex)
│   └── utils.ts
│
└── types/
    ├── incident.ts
    ├── timeline.ts
    ├── ioc.ts
    ├── task.ts
    ├── attachment.ts
    ├── user.ts
    ├── apiKey.ts
    └── api.ts
```

---

## 4. New Page: Incident List / Dashboard

The first screen after login. Replaces what would be a blank homepage.

```
┌──────────────────────────────────────────────────────────────────┐
│  IRDoc                                         + New Incident    │
│──────────────────────────────────────────────────────────────────│
│  [All] [Open] [Contained] [Closed]    Search...       Filter ▾  │
│──────────────────────────────────────────────────────────────────│
│  🔴 SEV-1  INC-2026-0315   Phishing — Finance Team      OPEN    │
│            SDP-2026-4421 ↗  · Opened 2h ago · 8 entries · 7 IOCs│
│            Assigned: John Doe                ████░ 60% tasks     │
│──────────────────────────────────────────────────────────────────│
│  🟡 SEV-2  INC-2026-0312   Suspicious Login — VPN        OPEN   │
│            Jira: SEC-881 ↗  · Opened 1d ago · 3 entries · 2 IOCs│
└──────────────────────────────────────────────────────────────────│
```

Each row shows:
- Severity badge and incident ref
- External reference badge with link icon (if present) — e.g., `SDP-2026-4421 ↗`
- Title, status, age, entry count, IOC count
- Assigned analyst
- Task progress bar

"New Incident" opens a modal: title, severity, template picker, assigned to. If the org has SDP/ManageEngine/Jira integration, there is also an optional "Link to existing ticket" field to manually attach an external ref.

---

## 5. Incident Topbar — External Reference Display

The topbar is the most frequently seen UI element. External refs must be clearly visible here.

```
┌────────────────────────────────────────────────────────────────────────────┐
│  🔴 SEV-1  │  Phishing Campaign — Finance Team  │  INC-2026-0315           │
│            │                                    │  SDP-2026-4421 ↗         │
│            │                                    │  [Copy ID] [Report] [Export]│
└────────────────────────────────────────────────────────────────────────────┘
```

`ExternalRefBadge` component:
```tsx
// components/common/ExternalRefBadge.tsx
export function ExternalRefBadge({ ref }: { ref: IncidentExternalRef }) {
  const sourceLabels = {
    servicedesk_plus: 'SDP',
    manage_engine:    'ME',
    jira:             'Jira',
    servicenow:       'SN',
  };

  return (
    <a
      href={ref.external_url}
      target="_blank"
      rel="noopener noreferrer"
      className="chip chip-blue"
      title={`Open in ${ref.external_source}`}
    >
      {sourceLabels[ref.external_source] ?? ref.external_source}
      -{ref.external_ref} ↗
    </a>
  );
}
```

If the incident has no external refs, this space is empty. If it has multiple (rare), they stack as small badges.

---

## 6. Key Component Specifications

### 6.1 `AddEntryForm.tsx`

- `entry-date` auto-set to today on mount and after each successful submission
- `entry-time` auto-set to current local time, updates every second while form is focused
- Global paste listener — if user pastes a screenshot anywhere on the page while this component is mounted, it captures the image and adds it to pending attachments
- Attachments previewed inline before submission
- On submit: POST timeline entry, then upload each pending attachment linked to the new entry ID
- After success: form resets, auto-switches to timeline view, new entry appears at top with slide-in animation

```tsx
// Auto-updating time while form is open
useEffect(() => {
  const interval = setInterval(() => {
    setCurrentTime(format(new Date(), 'HH:mm:ss'));
  }, 1000);
  return () => clearInterval(interval);
}, []);
```

### 6.2 `TimelineEntry.tsx`

- Card hover reveals action buttons (copy, pin, delete) via CSS `group-hover`
- Entry type drives dot color and badge — exact color map from prototype
- Pinned entries show pin icon with a highlighted left border accent
- Clicking an image attachment opens a lightbox; non-image triggers download via the signed URL
- `occurred_at` displayed in user's configured timezone

### 6.3 `TasksPanel.tsx`

- Loaded from `GET /api/v1/incidents/{id}/tasks`
- Tasks grouped by `phase` field, matching the prototype's grouping exactly
- Click to toggle: optimistic UI update, then `PUT` to API
- Progress bar recalculates on every toggle
- Panel: 280px fixed width, always visible
- Mobile (< 768px): collapses to a floating button that opens a bottom drawer

### 6.4 `AttachmentZone.tsx`

```tsx
useEffect(() => {
  const handlePaste = (e: ClipboardEvent) => {
    const items = Array.from(e.clipboardData?.items || []);
    items.forEach(item => {
      if (item.type.startsWith('image/')) {
        const file = item.getAsFile();
        if (file) onFileAdded(file);
      }
    });
  };
  document.addEventListener('paste', handlePaste);
  return () => document.removeEventListener('paste', handlePaste);
}, []);
```

### 6.5 `IOCTable.tsx` — Auto-detect on paste

When a user pastes multi-line text into the IOC value field, `iocDetector.ts` scans it and shows a modal: "We found 3 IOCs — add all?" Each detected IOC shows its auto-detected type for confirmation before bulk-adding.

### 6.6 `APIKeysSection.tsx` (Settings page)

```
API Keys
Used by external tools (ServiceDesk Plus, ManageEngine, Jira) to create cases in IRDoc.

[+ Create API Key]

Name                    Prefix           Scopes             Last Used     Actions
SDP Integration         irp_key_a3f9...  incidents:create   5 min ago     [Revoke]
Automation Script       irp_key_b8c2...  incidents:read     Never         [Revoke]
```

Creating a key:
1. User sets name and selects scopes from checkboxes
2. POST `/api/v1/api-keys`
3. Modal shows full key ONE TIME: `irp_key_a3f92b8c...` with copy button and warning: "This key will not be shown again. Copy it now."
4. Key appears in list with prefix only from now on

---

## 7. Auth Flow

```
App loads
  → Check authStore for in-memory access_token
  → If none: render LoginPage
  → POST /auth/login → store access_token in Zustand (memory only — not localStorage)
  → Redirect to /incidents

API call returns 401
  → apiClient interceptor: POST /auth/refresh (HttpOnly cookie carries refresh token)
  → On success: retry original request with new token
  → On failure: clear store → redirect to /login
```

---

## 8. Real-Time Updates (WebSocket)

Socket.io events the frontend listens to:

```
Server → Client:
  "timeline:entry:added"     { entry }
  "timeline:entry:updated"   { entry }
  "timeline:entry:deleted"   { entry_id }
  "task:updated"             { task }
  "ioc:added"                { ioc }
  "incident:updated"         { incident }
  "report:ready"             { report_id }     ← used in Phase 3
  "sync:complete"            { policy_id, url } ← used in Phase 4

Client → Server:
  "join:incident"            { incident_id }
  "leave:incident"           { incident_id }
```

Presence indicator in the topbar: colored dots showing which analysts are active in this incident. "2 analysts online."

**Optimistic updates:** Timeline entries are added to local React Query cache immediately on submit. On API failure, the entry is rolled back and a toast is shown.

---

## 9. Routing Structure

```
/                          → redirect to /incidents
/login                     → LoginPage
/incidents                 → IncidentListPage
/incidents/:id             → IncidentWorkspacePage (default: /timeline)
/incidents/:id/timeline
/incidents/:id/iocs
/incidents/:id/summary
/incidents/:id/reports     → Shell in Phase 2, functional in Phase 3
/incidents/:id/integrations → Shell in Phase 2, functional in Phase 4
/settings                  → SettingsPage (profile, API keys, theme, notifications)
/admin                     → AdminPage (Phase 5: team management, org settings)
```

---

## 10. State Management

```ts
// authStore.ts
interface AuthStore {
  user: User | null;
  accessToken: string | null;
  setAuth: (user: User, token: string) => void;
  clearAuth: () => void;
}

// themeStore.ts — persisted to localStorage
interface ThemeStore {
  theme: 'dark' | 'light';
  toggle: () => void;
}

// uiStore.ts
interface UIStore {
  activeSection: string;
  toasts: Toast[];
  addToast: (msg: string, type: 'success' | 'error' | 'info') => void;
  removeToast: (id: string) => void;
  activeModal: string | null;
  openModal: (name: string) => void;
  closeModal: () => void;
}
```

React Query handles all server state (incidents, timeline, IOCs, tasks). Zustand handles UI state and auth only.

---

## 11. PremiumGate Component

Used throughout the app to wrap premium features. The gated content renders but is visually dimmed and overlaid with a lock + upgrade prompt.

```tsx
// components/common/PremiumGate.tsx
export function PremiumGate({ feature, children }: { feature: string; children: ReactNode }) {
  const { flags } = useFeatureFlags();

  if (flags[feature]) return <>{children}</>;

  return (
    <div className="relative">
      <div className="pointer-events-none opacity-40 select-none">
        {children}
      </div>
      <div className="absolute inset-0 flex flex-col items-center justify-center
                      bg-bg-elevated/80 rounded-card backdrop-blur-sm gap-2">
        <span className="text-2xl">🔒</span>
        <p className="text-sm font-semibold text-text-primary">Premium Feature</p>
        <a href="https://irpdoc.io/pricing"
           className="text-xs text-accent underline">
          Upgrade to unlock →
        </a>
      </div>
    </div>
  );
}
```

---

## 12. Frontend Docker Setup

```dockerfile
# frontend/Dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json .
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

```nginx
server {
  listen 80;
  root /usr/share/nginx/html;
  index index.html;

  location /api {
    proxy_pass http://backend:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
  }

  location /socket.io {
    proxy_pass http://backend:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
  }

  location / {
    try_files $uri $uri/ /index.html;
  }
}
```

---

## 13. Accessibility & Performance

- All interactive elements reachable by keyboard
- Keyboard shortcuts: `N` — focus Add Entry form, `Escape` — close any modal
- `aria-label` on all icon-only buttons
- Color is never the only meaning carrier — badges always include text
- Code-split by route (Vite lazy imports) — initial bundle target < 200KB gzipped
- Timeline virtualized if entry count > 100 (`@tanstack/react-virtual`)

---

## 14. Deliverables Checklist

### Designer
- [ ] Design tokens validated in Tailwind config (match prototype exactly)
- [ ] Incident List page designed
- [ ] Login page designed
- [ ] New Incident modal designed
- [ ] External ref badge designed (SDP, Jira, ManageEngine variants)
- [ ] API Keys section in settings designed
- [ ] All interaction states documented (hover, loading, empty, error)

### Developer (Frontend)
- [ ] Vite + React + TypeScript + Tailwind scaffold
- [ ] CSS variables global.css (dark + light)
- [ ] API client (Axios + refresh interceptor)
- [ ] Auth (Login page, token management, protected routes)
- [ ] Incident List page with external ref display
- [ ] AppShell (LeftNav + TopBar + TasksPanel)
- [ ] TopBar with ExternalRefBadge component
- [ ] Timeline page (Add + View + Filters + CSV export)
- [ ] AttachmentZone (drag/drop + global paste)
- [ ] IOC page (table + inline add + auto-detect modal)
- [ ] Summary page (stat cards + editable sections)
- [ ] Report page (shell — cards shown, generation non-functional)
- [ ] Integrations page (shell — toggle cards shown, non-functional)
- [ ] Settings page (profile + theme + notifications + API keys section)
- [ ] APIKeysSection (create with one-time display, list with prefix, revoke)
- [ ] Toast notification system
- [ ] PremiumGate component
- [ ] WebSocket integration (real-time entries + presence)
- [ ] Theme toggle (persisted)
- [ ] Nginx Dockerfile

### QA
- [ ] All sections render without errors in both themes
- [ ] Add/edit/delete timeline entry works end-to-end
- [ ] Screenshot paste captured and uploaded correctly
- [ ] File upload works (image + non-image, verifies SHA-256 in DB)
- [ ] IOC auto-detect modal shows on paste of multi-IOC text
- [ ] Task toggle persists to API
- [ ] External ref badge shows and links correctly (test with inbound webhook)
- [ ] API key creation shows key once only, then prefix only
- [ ] API key revoke works
- [ ] Two browser tabs show real-time timeline sync
- [ ] PremiumGate shows correctly for core-only org
- [ ] 401 refresh flow transparent to user

### Product Owner
- [ ] Visual comparison: React app matches HTML prototype at 95%+ fidelity
- [ ] Full workflow: create incident via webhook, open in UI, add entries, tick tasks, see external ref

---

*Next: Phase 3 — Report Template Builder & Report Generation*
