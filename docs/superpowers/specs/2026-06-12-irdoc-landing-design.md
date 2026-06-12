# IRDoc Landing Page — Design Spec

**Date:** 2026-06-12  
**Domain:** irdoc.io  
**Hosting:** Cloudflare Pages  
**Status:** Approved — ready for implementation

---

## Overview

A single-file static landing page (`index.html`) for IRDoc — an early-stage, self-hosted incident response documentation platform. The page presents IRDoc as in active development with a public alpha shipping Q4 2026, and collects waitlist emails via a Cloudflare Worker backed by KV storage. Everything on the page is free and self-hosted — no premium tier, no SaaS.

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Hero animation | Path draw-in (A) + ambient orbs/particles (B) | Most cinematic; orbs give atmospheric depth, path draw gives identity moment |
| Page structure | Hybrid cinematic (Approach 3) | Cinematic hero + polished feature sections + roadmap + waitlist |
| Waitlist form | Inline section (A) | Lower friction; always visible; no click required |
| Default theme | Dark | Brand identity; dark is default, light available via toggle |
| Email storage | Cloudflare Workers + KV | No third-party tools; data stays in user's CF account |

---

## Page Sections (top to bottom)

### 1. Navigation
- Fixed top bar, dark backdrop with `backdrop-filter: blur(16px)`
- Left: IRDoc logo (uses `irdoc_dark.svg` in dark mode, `irdoc_light.svg` in light mode) + wordmark
- Center: `Features`, `Roadmap`, `Docs`, `GitHub`
- Right: dark/light mode toggle (sun/moon icon, persisted in `localStorage`) + `Join Waitlist` accent button
- Scrolled state: adds `box-shadow` and solidifies border

### 2. Hero — Cinematic Opener
- Full viewport height (`100vh`)
- Background: `#080b12` with subtle grid overlay
- **Ambient atmosphere (always on):** Three blurred orbs (orange, blue, purple) + ~8 floating particles that drift upward and fade; particles are orange, blue, and yellow variants
- **Logo draw-in sequence:** The IRDoc SVG (`irdoc_dark.svg`) paths animate in using `stroke-dasharray` / `stroke-dashoffset` — paths draw stroke by stroke over ~2.5s
- **Content reveal (after logo):** Badge → headline → subheadline → CTA row → social proof bar, each fading in with a 150ms stagger
- Headline: *"Incident response docs, without the chaos."*
- Subheadline: *"Self-hosted IR workspace for SOC teams. Timeline-first, local-AI assisted, SharePoint-synced."*
- CTAs: `⚡ Join the waitlist` (orange) + `See features →` (ghost)
- Social proof bar: `🐳 Docker in <3 min` · `🔒 Self-hosted` · `AGPL-3.0` · `🤖 Local AI`
- Gradient fade at bottom to blend into next section

### 3. Integration Ticker
- Scrolling horizontal strip, dark background
- Left/right gradient fade masks
- Items (no CrowdStrike, no Proofpoint):
  - VirusTotal · AbuseIPDB · Shodan · Microsoft Sentinel · Azure AD / Entra · Slack / Teams · ServiceDesk Plus · Jira / ServiceNow · SharePoint · Ollama / Claude / OpenAI

### 4. Feature Bento Grid
- Section label: `Core Platform`
- Headline: *"Everything your SOC team needs. Nothing they don't."*
- 3-column bento grid, 6 cards — all tagged as free/core (no premium tags)
- Each card has a looping micro-animation:

| Card | Animation |
|------|-----------|
| Timeline-First Investigation (wide, 2col) | Timeline entries slide in one by one on loop |
| IOC Auto-Enrichment | Confidence bars animate width (red/orange/yellow) |
| Local AI Reports | Typewriter cursor effect, "Generating executive summary…" |
| Report Template Builder | Drag blocks slide left on hover, subtle shuffle loop |
| SharePoint Auto-Sync | Green pulse dot, sync status text cycles |
| Structured Task Playbooks | Checkboxes tick themselves off on loop |

### 5. Report Builder Showcase
- Layout: left text column + right animated mockup
- Text: headline *"Reports for every audience"*, description of drag-and-drop composition, audience pills (Management Brief / Technical Report / Legal Compliance), export formats (PDF · DOCX · Markdown · HTML)
- Mockup: browser chrome with builder UI — blocks animate in on scroll with `translateX` stagger; hover on blocks shows drag intent (slight horizontal shift + orange border)
- Scroll-triggered: blocks slide in from left when section enters viewport

### 6. SharePoint Auto-Sync Showcase
- Layout: left mockup + right text (flipped)
- Text: headline *"Management is always up to date"*, 60s debounce explanation, "they never need IRDoc access" callout
- Mockup: sync status panel with green pulse dot, cycling "Last synced X ago" text, animated sync event log (new entries appear on interval)

### 7. Roadmap
- Vertical timeline, left-aligned
- Connecting line: gradient from `--border` through `--orange` 
- Milestones:

| Dot | Label | Tag |
|-----|-------|-----|
| 🟢 Green | Core Incident Workspace | ✓ Shipped |
| 🟢 Green | Report Builder + Local AI | ✓ Shipped |
| 🟢 Green | SharePoint Auto-Sync | ✓ Shipped |
| 🟢 Green | Integrations & SSO | ✓ Shipped |
| 🟠 Orange (glowing pulse) | **Alpha Release** | ⚡ Q4 2026 |
| ⚪ Grey | Multi-tenancy + MSSP mode | 2027 |

- Scroll-reveal: each milestone fades in as it enters viewport

### 8. Waitlist CTA Section
- Full-width, centered
- Background: dark with orange radial glow behind the form
- Counter badge: `● N people on the list` (green pulse dot; count loaded from Worker response or hardcoded initial value)
- Headline: *"Stop writing incident reports by hand."*
- Subheadline: *"IRDoc alpha ships Q4 2026. Enter your email and we'll send you an invite — no marketing, no SaaS pitch, just access."*
- Form: email `<input>` + `Join →` button (full inline row, max-width 420px)
- Success state: input row replaced by `✓ You're on the list. We'll reach out when alpha is ready.`
- Error state: inline red message below input
- Fine print: *"Stored securely in Cloudflare KV · No third-party email tools · You write the invites yourself"*

### 9. Footer
- Logo (SVG icon + wordmark)
- Links: Features · Roadmap · Docs · GitHub · Changelog · License
- Legal: `AGPL-3.0 · Self-hosted · © 2026 IRDoc`

---

## Dark / Light Mode

- **Default:** Dark (`--bg: #080b12`, `--text: #e6edf3`, `--accent: #f97316`)
- **Light palette:** `--bg: #f8fafc`, `--text: #053059` (IRDoc navy), `--accent: #f86d05`
- Toggle via `data-theme="light"` on `<html>`; persisted in `localStorage('irdoc-theme')`
- Nav logo swaps SVG src: `irdoc_dark.svg` → `irdoc_light.svg` (both embedded inline as `<img>`)
- Favicon: `irdoc_light_32x32.ico` (tab icon, works on both modes)
- Smooth transition: `transition: background 0.3s, color 0.3s` on `:root`

---

## Animations Summary

| Animation | Trigger | Technique |
|-----------|---------|-----------|
| Logo path draw-in | Page load | `stroke-dasharray` + `stroke-dashoffset` CSS keyframe |
| Hero orbs float | Always | CSS `@keyframes` translate Y loop |
| Hero particles drift | Always | CSS `@keyframes` translate X/Y with stagger |
| Hero content stagger | After logo (~3s) | CSS animation with `animation-delay` |
| Scroll reveals | Viewport entry | `IntersectionObserver` adds `.visible` class |
| Bento card micro-animations | Continuous loop | CSS `@keyframes` (no JS required) |
| Builder blocks slide in | Viewport entry | `IntersectionObserver` + `translateX` |
| SP sync log pulse | Continuous | `setInterval` updating text |
| Roadmap milestone reveal | Viewport entry | `IntersectionObserver` with stagger |
| Waitlist counter | On load | Fetch from Worker `/api/waitlist/count` or static |

---

## Cloudflare Backend

### Architecture
```
irdoc.io (CF Pages)
  └── /api/waitlist          POST  → functions/api/waitlist.js
  └── /api/waitlist/count    GET   → functions/api/waitlist.js (method branch)
```

### Pages Function: `functions/api/waitlist.js`
- **POST:** Validate email format → check KV for duplicate → store `{email, timestamp, source}` → return `{success: true, count: N}`
- **GET /count:** Return `{count: N}` (read KV metadata or a counter key)
- **KV namespace:** `WAITLIST` bound in `wrangler.toml`
- Key format: `email:<sha256-of-email>` → value: `{email, timestamp}`
- Rate limit: 5 submissions per IP per hour (CF Worker `waitUntil` + KV TTL key)
- **Optional:** On new signup, send notification via Cloudflare Email Routing to `spinu.petru.boris@gmail.com`

### wrangler.toml
```toml
name = "irdoc-landing"
compatibility_date = "2024-01-01"

[[kv_namespaces]]
binding = "WAITLIST"
id = "..."  # created via wrangler kv:namespace create WAITLIST

[site]
bucket = "./"
```

### Admin export
```bash
wrangler kv:key list --namespace-id=<ID> | jq '.[].name'
# or visit /admin/waitlist (protected by CF Access or a secret header)
```

---

## File Structure

```
landing/                        # or project root for CF Pages
├── index.html                  # Single self-contained file
├── irdoc_dark.svg              # From --temp/
├── irdoc_light.svg             # From --temp/
├── irdoc_light_32x32.ico       # Tab favicon
├── functions/
│   └── api/
│       └── waitlist.js         # CF Pages Function
└── wrangler.toml               # CF Pages + KV config
```

The `index.html` is entirely self-contained: Google Fonts loaded via `<link>`, all CSS inline in `<style>`, all JS inline in `<script>`. No build step, no npm, no framework.

---

## Typography & Tokens (unchanged from existing design)

- `--sans: 'Syne', sans-serif` — headings and body
- `--mono: 'JetBrains Mono', monospace` — badges, timestamps, code
- `--accent: #f97316` (orange) · `--accent-2: #fb923c`
- Border radius: `12px` cards, `8px` buttons, `100px` badges

---

## Out of Scope

- No backend login / authentication
- No CrowdStrike or Proofpoint references anywhere on the page
- No premium tier, no pricing section — everything is free and self-hosted
- No marketing email platform (Mailchimp, SendGrid, etc.)
- No analytics beyond what Cloudflare Pages provides natively
