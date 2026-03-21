# IRDoc Platform — UX Research Bug Report

> Conducted by UX Research Agent | March 2026
> 35 issues identified across Critical / High / Medium / Low severities

---

## Summary

| Severity | Count |
|----------|-------|
| 🔴 Critical | 3 |
| 🟠 High | 7 |
| 🟡 Medium | 10 |
| 🟢 Low | 15 |
| **Total** | **35** |

---

## 🔴 Critical

- [ ] **[websocket.ts] Silent WebSocket failures** — Socket.io has no error handler or reconnection indicator. When it fails (404s seen in logs), real-time updates (timeline, IOC enrichment, report:ready) stop working with no notification to the user. Add a connection-status indicator and fallback polling on failure.

- [ ] **[apiClient.ts] Mid-work session expiry with no warning** — When the refresh token expires, the user is silently logged out during any API call (e.g., mid-timeline-entry). Work may be lost. No pre-expiry warning, no explanation on logout. Should detect impending expiry and warn user.

- [ ] **[AddEntryForm.tsx] Attachment upload failures lost behind success toast** — Success toast is shown after the timeline entry is created, but file uploads run in a separate loop afterwards. If any file upload fails, the user only sees individual error toasts after already seeing "Entry added". Users may not notice which attachments are missing. Show a consolidated result: "Entry added. 2 of 3 attachments uploaded."

---

## 🟠 High

- [ ] **[Modal.tsx] Backdrop click may hit elements behind the modal** — The backdrop `onClick` handler checks `e.target === e.currentTarget`, but this condition can fail for nested child divs, causing the modal not to close. Additionally, no `stopPropagation` means buttons behind the modal could be triggered by accident.

- [ ] **[IncidentWorkspacePage.tsx] Incident not found page has no recovery action** — When an incident doesn't exist (deleted or no access), the user sees a static "not found" message with no button to go back to the list and no explanation (permissions vs. deleted). Add a "Back to Incidents" button and contextual messaging.

- [ ] **[LoginPage.tsx] Setup status check silently swallowed** — `apiClient.get('/auth/setup-status')` errors are caught with `.catch(() => {})`. If the backend is unreachable on first boot, the setup wizard never shows and the user is stranded at the login form with no explanation.

- [ ] **[IOCPage.tsx] Bulk IOC import sends raw text, not selected IOCs** — The auto-detect modal lets users select which IOCs to add, but `bulkImport.mutateAsync()` sends the raw pasted text to the backend, which re-detects. If backend and frontend regex patterns differ, different IOCs are added than what the user selected. Send the explicitly selected IOC list instead.

- [ ] **[ReportPage.tsx] Report generation polling has no timeout** — When a report is generating, the frontend polls every 3 seconds indefinitely. If the worker crashes and the report stays in `generating` state forever, polling never stops. Add a max-timeout (e.g., 5 minutes) and show an error with a retry option.

- [ ] **[AdminPage.tsx] Non-admin redirect causes blank screen flash** — The admin role redirect runs in `useEffect`, so the component renders `null` for a frame before navigation. Non-admin users see a blank white flash. Guard the route earlier (in the router or with a loading spinner).

- [ ] **[AddEntryForm.tsx] No upload progress for large file attachments** — Files up to 50MB are supported but the UI shows no progress bar, speed estimate, or cancel option during upload. On slow connections, the app appears frozen. Add per-file progress using `onUploadProgress` in the Axios config.

---

## 🟡 Medium

- [ ] **[uiStore.ts] All toasts dismiss in 4s regardless of severity** — Critical error messages (e.g., "Failed to save report") disappear in 4 seconds before the user has time to read them. Errors should persist longer (6–8s), successes shorter (2–3s), and errors should be more visually distinct.

- [ ] **[AttachmentZone.tsx] No limit on number of files queued** — Users can queue hundreds of files, each triggering a separate POST request. Add a max file count warning (e.g., "Maximum 20 files per entry") and validate total size before submit.

- [ ] **[IOCPage.tsx] Confidence score has no contextual label** — The confidence field (0–100) is a bare number input with no indication of what ranges mean. Show a dynamic label ("Low / Medium / High / Critical") based on the value to help analysts calibrate.

- [ ] **[IncidentListPage.tsx] No pagination — all incidents fetched at once** — `useIncidents()` fetches all incidents without `page`/`per_page` params. Orgs with hundreds of incidents will see slow loads. The API supports pagination; the frontend should use it and show page controls.

- [ ] **[App.tsx] Flash of login page during session restore** — On page refresh, `tryRestore()` is async. Before it completes, `ProtectedRoute` sees no user and renders `LoginPage`, then redirects to the incident list after restore succeeds. Show a full-screen loading state during the restore phase.

- [ ] **[AddEntryForm.tsx] Auto-updating time overwrites user input** — The time field updates every second via interval while the form is focused. If a user is trying to type a past time (e.g., "14:30"), the field resets underneath them. Stop auto-updating as soon as the user edits the time field manually.

- [ ] **[TimelineEntry.tsx] Lightbox has no close button and can't be closed by clicking the image** — The image lightbox only closes by clicking the dark backdrop. Clicking the image itself does nothing. Add a visible ✕ close button and make the image click propagate to close.

- [ ] **[LoginPage.tsx] All errors use identical styling regardless of cause** — "Invalid credentials" (user error) and "Server unavailable" (system error) look identical. Distinguish between user-fixable errors and system errors. Show a retry button for transient failures.

- [ ] **[SummaryPage.tsx] Stats don't refresh when timeline/IOCs updated via WebSocket** — `useIncidentStats()` is not invalidated by `timeline:entry:added` or `ioc:added` WebSocket events. Stats on the Summary tab show stale counts until a manual page refresh. Add query invalidation in the WebSocket handler.

- [ ] **[TimelineEntry.tsx / IOCPage.tsx] Native `confirm()` dialogs for destructive actions** — Delete confirmations use the browser's native `window.confirm()`, which is unstyled, inconsistent with the app's design, and disabled in some browser configs. Replace with the custom `Modal` component.

---

## 🟢 Low

- [ ] **[TopBar.tsx] Incident reference (INC-YYYY-NNNN) not copyable** — The incident ref is plain text. Like ExternalRefBadges, it should be clickable to copy to clipboard, which analysts frequently need for ticketing and Slack.

- [ ] **[LoadingSpinner.tsx] Generic spinner with no context label** — Every loading state shows the same spinner with no text. Add an optional `label` prop (e.g., "Loading timeline…") to communicate what's happening.

- [ ] **[TimelinePage.tsx] "Press N" keyboard shortcut is not discoverable** — The shortcut is mentioned only in the empty state. There's no persistent hint in the UI, help menu, or tooltip. Add a keyboard shortcut hint near the Add Entry button.

- [ ] **[Modal.tsx] No "Press ESC to close" indicator** — Escape key closes modals but there's no visual hint. Add a small tooltip or a hint text near the close button.

- [ ] **[ExternalRefBadge.tsx] Long external refs can overflow** — Very long external reference values (full URLs, long Jira keys) may overflow the TopBar layout. Add `text-overflow: ellipsis` with a tooltip for the full value.

- [ ] **[TasksPanel.tsx] Fixed 280px width not responsive** — On narrow viewports (laptop, tablet), the tasks panel takes up too much horizontal space. Make the panel collapsible or responsive.

- [ ] **[IOCPage.tsx] No clipboard feedback when copying IOC values** — Clicking an IOC value copies it (good) but only has a `title="Click to copy"` tooltip. Add a brief "Copied!" toast or inline feedback on success.

- [ ] **[ReportPage.tsx] "Failed" report status shows no error detail** — Failed reports display a red chip with no way to see why they failed. Show the error message on hover or in an expandable row.

- [ ] **[PremiumGate.tsx] Premium content briefly flashes unlocked on slow feature flag fetch** — Content is always rendered in the DOM (dimmed if locked), so on a slow feature flag response, premium UI momentarily appears fully unlocked. Consider hiding content until flags are loaded.

- [ ] **[IncidentTemplatesPage.tsx (Admin)] New task row has no "Cancel" option** — When adding a new task via the inline form, there's no way to cancel — only add. Add an ✕ or Cancel button to discard the new row.

- [ ] **[Modal.tsx] `size` and `maxWidth` props can conflict** — The Modal component has both a `size` enum and a `maxWidth` override. If both are passed, they conflict silently. Consolidate to one sizing API.

- [ ] **[AddEntryForm.tsx] Timer interval dependency on `[focused]` recreates interval on every focus change** — Minor memory/performance issue. The interval is correctly cleaned up, but recreated on every focus toggle. Use a ref to track the last-set time and only update state when the user hasn't manually edited.

- [ ] **[SettingsPage] Password change has no "confirm password" field** — Users can set a new password with a single field and no confirmation, risking typos that lock them out. Add a confirmation field with match validation before enabling the submit button.

- [ ] **[IOCPage.tsx] Expanded enrichment row looks disconnected from its IOC row** — The enrichment details panel opens as a full-width row below the IOC, but has no visual connector (arrow, highlight, indent) tying it to the parent row. Add a left border or background tint to clarify hierarchy.

- [ ] **[TimelinePage.tsx] No visual feedback when pinning/unpinning an entry** — The pin action succeeds silently. Add a brief inline animation or icon state change to confirm the pin was registered.
