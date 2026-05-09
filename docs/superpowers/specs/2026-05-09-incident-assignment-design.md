# Incident Assignment — Design Spec

**Date:** 2026-05-09  
**Status:** Approved

---

## Overview

Add the ability to assign incidents to analysts. Incidents default to **unassigned**. Any team member can claim ("pick up") an unassigned incident with one click. Any analyst or admin can also reassign to a different team member.

---

## Scope

- No database migration required — `incidents.assigned_to` (FK → `users.id`, nullable) already exists in the schema.
- Changes span: backend incident service, backend user listing, frontend types, frontend hooks, incident list page, and TopBar.

---

## Backend

### 1. Enrich `IncidentOut` with assignee details

**Problem:** `IncidentOut.assigned_to` is currently a bare UUID. The frontend needs a name and initials to render the assignee without a separate lookup per incident.

**Solution:** Add a nested `assigned_user` field to `IncidentOut`:

```python
class UserBrief(BaseModel):
    id: UUID
    full_name: str
    email: str
    avatar_initials: str | None

    model_config = {"from_attributes": True}

class IncidentOut(BaseModel):
    ...
    assigned_to: UUID | None
    assigned_user: UserBrief | None = None  # populated by service layer
```

**Service layer:** In `incident_service.py`, eager-load the assigned user relationship when fetching incidents. The `Incident` model already has a `created_by` FK — add a parallel `assignee` relationship pointing to `users` via `assigned_to`.

**Model relationship to add** in `incident.py`:
```python
assignee: Mapped["User | None"] = relationship(
    "User", foreign_keys=[assigned_to], lazy="noload"
)
```

Then in the service, use `selectinload(Incident.assignee)` when querying incidents.

### 2. Users listing endpoint

`GET /api/v1/users` exists and returns org members. Two changes required:

**Permission fix:** `users.read` is currently `admin`-only in `permissions.py`. Lower it to `viewer` — every org member can see who else is in their org. This is a prerequisite for non-admin users to populate the picker.

**Schema fix:** `UserOut` in `schemas/admin.py` is missing `avatar_initials`. Add it:
```python
class UserOut(BaseModel):
    id: UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    avatar_initials: str | None  # add this
    created_at: datetime
```

**Filter:** Add `.where(User.is_active == True)` to the `list_users` query so deactivated users don't appear in the picker.

### 3. `IncidentUpdate` (already supports `assigned_to`)

No changes needed — `assigned_to: str | None` is already present in `IncidentUpdate`. Passing `null` unassigns the incident.

---

## Frontend

### Types (`src/types/incident.ts`)

Add to `Incident`:
```ts
interface UserBrief {
  id: string
  full_name: string
  email: string
  avatar_initials: string | null
}

interface Incident {
  ...
  assigned_to: string | null
  assigned_user: UserBrief | null
}
```

Add to `UpdateIncidentPayload`:
```ts
assigned_to?: string | null
```

### Hook (`src/hooks/useOrgUsers.ts`) — new file

```ts
function useOrgUsers(): { data: UserBrief[], isLoading: boolean }
```

Fetches `GET /api/v1/users` and returns active org members. Cached via React Query with a 60-second stale time (user list changes infrequently).

### Incident List Page (`src/pages/IncidentListPage.tsx`)

Each incident card gains two new elements on the right side, before the status chip:

1. **Assignee display** — when assigned: avatar circle showing initials (or first letter of name) + full name truncated to ~12 chars. When unassigned: a muted "— Unassigned" text label.

2. **"Pick up" button** — shown only when the incident is unassigned. A ghost `btn-sm` button reading "Pick up". Clicking calls `updateIncident({ assigned_to: currentUser.id })` with `e.stopPropagation()` to prevent card navigation. Disappears once assigned.

The card click handler navigates to the incident as before — the Pick up button stops propagation so it doesn't also navigate.

### TopBar (`src/components/layout/TopBar.tsx`)

Add an assignee chip between the status `<select>` and the action buttons area.

**When assigned:** Renders a pill showing initials avatar (24px circle, accent background) + assignee full name. Clicking opens an inline `<select>` (same pattern as status/severity) listing all active org members + a "— Unassign" option at the top.

**When unassigned:** Renders a muted "— Unassigned" chip. Clicking opens the same picker.

**Implementation:** Use a controlled `<select>` styled as a chip, same as the status select added previously. The select value is the assignee user ID (or empty string for unassigned). `onChange` calls `updateIncident({ assigned_to: value || null })`.

The org users list is loaded via `useOrgUsers()` inside TopBar.

---

## Interaction Flow

```
List page — unassigned incident:
  [SEV-2] [INC-2026-0001] Title...  [— Unassigned] [Pick up]  [OPEN]

  → user clicks "Pick up"
  → updateIncident({ assigned_to: currentUser.id })
  → card re-renders: [SEV-2] [INC-2026-0001] Title...  [PB Pete B.]  [OPEN]

List page — assigned incident:
  → "Pick up" button hidden
  → assignee name shown

TopBar — any tab:
  [SEV-2] [INC-2026-0001]  Title  [PB Pete B. ▼]  [OPEN ▼]  [Copy ID] [Report]

  → user clicks assignee chip
  → dropdown opens with all active org members + "— Unassign" at top
  → selecting a user calls updateIncident({ assigned_to: userId })
  → chip updates immediately via React Query cache invalidation
```

---

## Error Handling

- On failed assignment update: show error toast ("Failed to update assignee"), no optimistic update rollback needed since we await the mutation.
- If `useOrgUsers` fails to load: picker shows a "Could not load team" disabled option; existing assignee still displays.

---

## Out of Scope

- Assignment notifications (Slack/email) — Phase 4 integration concern.
- Assignment history / audit trail — audit log already captures all `incidents` updates via the existing audit service.
- Filtering incidents by assignee on the list page — can be added as a follow-up filter chip.
- Auto-assign on create — user explicitly said default is unassigned.
