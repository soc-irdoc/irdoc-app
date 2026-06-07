# AI-Assisted Report Generation

IRDoc includes a local AI agent that automatically keeps your incident reports up to date as the
incident evolves. It runs entirely on-premises using [Ollama](https://ollama.com/) — no data
leaves your network.

---

## How It Works — Overview

1. A human analyst generates the **first report** for an incident using a custom template.
   This is the **seed report** and signals that AI should maintain this template going forward.
2. Every time the incident changes (timeline entry, task update, IOC added, status change),
   the AI agent is triggered after a configurable debounce delay.
3. The agent generates a **new versioned report** for every template marked for AI auto-generation
   that already has a seed report on this incident.
4. Each new version receives the previous version's narrative as context, producing
   **delta-aware updates** — stable sections stay unchanged, only what the new evidence
   requires is rewritten.
5. All versions are preserved. Nothing is ever overwritten.

---

## The Seed Requirement

The AI agent will **never generate a report from scratch** for a template that has not been
manually generated first.

This is intentional:

- The first report sets the structure, tone, and classification for that template on that incident.
- The AI then takes over maintenance, building a versioned chain on top of the human's foundation.
- Turning on `AI Auto-Generate` for a template does not trigger an immediate generation —
  it only activates the agent once a human generates the first report.

**Flow:**

```
Human generates Management Report v1  →  AI is now active for this template on this incident
Incident changes  →  AI generates Management Report v2  (delta-aware, uses v1 as context)
Incident changes  →  AI generates Management Report v3  (delta-aware, uses v2 as context)
```

If Technical Report was never manually generated, the AI skips it even if the template is
flagged — until a human generates Technical Report v1.

---

## Multi-Template Support

You can enable AI auto-generation independently per template. Each template maintains its
own independent version chain, scoped to the incident.

**Example with three templates all flagged:**

| Template | Seed generated? | AI chain |
|---|---|---|
| Management Report | Yes (human generated v1) | v1 → v2 → v3 … |
| Technical Report | Not yet | Skipped until human generates v1 |
| Legal Report | Yes (human generated v1) | v1 → v2 … |

Each chain is completely independent. Management v3 always uses Management v2 as delta
context — never Technical v2.

---

## Enabling AI Auto-Generate on a Template

1. Go to **Report Templates** in the admin navigation.
2. Find the custom template you want to activate.
3. Click **AI On / AI Off** to toggle `ai_auto_generate` for that template.
4. The button turns highlighted when active. An **AI** chip appears on the template name.

> System templates cannot be toggled — clone them first to get an editable copy.

---

## AI Configuration

The AI agent is configured under **Integrations → AI** in the admin panel.

| Setting | Description | Default |
|---|---|---|
| **Enable AI** | Master switch. Off = no AI reports generated. | Off |
| **Ollama Base URL** | URL of the Ollama instance. Use `http://ollama:11434` for the bundled service. | `http://ollama:11434` |
| **Model Name** | Ollama model identifier (e.g. `llama3.2`, `mistral`, `qwen2.5`). Must be pulled first. | `llama3.2` |
| **Debounce Delay** | Seconds to wait after the last incident change before generating. Prevents a burst of edits from producing many reports. Min 10s, max 3600s. | 60 |
| **Max Timeline Events** | How many timeline entries are included in the AI prompt. Increase for more detail; decrease if your model has a small context window. | 20 |

**Test Connection** checks that Ollama is reachable and that the configured model is available.
If the model is not found, it returns an actionable error message with the pull command.

---

## Audience-Aware Prompting

The AI agent tailors its output to the **Destination** set on each report template.
This is what makes a Management Report read differently from a Technical Report or a Legal Report
— the same incident data produces three distinct narratives because the AI is given a
different persona and set of priorities for each audience.

The destination is configured when you create or edit a report template (the **Destination**
dropdown in the template builder).

### Management

**AI persona:** Senior IR analyst writing for executive leadership.

**Focus:**
- What happened at a high level
- Business impact and affected users
- What the team did and the current status
- Next steps for leadership decision-making

**Style:** Plain language, no technical jargon. 3–5 clear sentences. Past tense for resolved
items. No bullet points. Suitable for a board briefing or executive status update.

---

### Analyst (Technical)

**AI persona:** Senior technical IR analyst writing for the response team.

**Focus:**
- Attack vectors and TTPs observed
- Specific IOC values (hashes, IPs, domains, file paths)
- Affected systems and technical timeline
- Technical remediation steps taken and pending
- Gaps in the evidence chain

**Style:** Technical and specific. References IOC values and entry types from the incident
data directly. Can use numbered sections. Suitable for internal IR team review and handoffs.

---

### Legal

**AI persona:** IR analyst writing for legal counsel and compliance review.

**Focus:**
- Precise chronological timeline of events
- Chain of evidence — who did what and when
- Affected data and systems
- Regulatory implications suggested by the evidence
- What has and has not yet been determined

**Style:** Plain, precise language suitable for legal proceedings. Heavily hedged — every
claim is explicitly grounded in the evidence provided. Uses phrases like
*"Based on currently available evidence..."* and *"It has not yet been determined whether..."*.
Avoids technical jargon. Avoids speculation.

---

### Custom

**AI persona:** Defaults to the Management persona (safe, conservative baseline).

Use `Custom` when your template's audience does not fit the three named categories.
The output is a clear, non-technical executive narrative.

---

## Delta-Aware Versioning

From v2 onwards, the AI receives the previous version's full narrative alongside the current
incident data. Its instructions for a delta update are:

1. Keep all sections that have **not changed** exactly as they were — same wording, same structure.
2. Update **only** sections affected by new evidence, timeline events, or status changes.
3. If any statement in the previous version now contradicts the current evidence, flag it:
   `NOTE: Previous assessment [quote] is superseded by [new finding].`
4. Use hedged language for preliminary findings.
5. Never introduce facts not present in the provided data.

This produces reports that are **stable over time** — an analyst reviewing v3 next to v1
sees exactly what changed and what did not, rather than a completely rewritten document.

---

## Evidence-First Principle

The AI agent operates under a strict evidence-first constraint that applies to all audiences
and all versions:

- It may only use data present in the incident record (timeline, IOCs, tasks, metadata).
- It may not introduce facts, names, or conclusions not supported by the provided data.
- Where confidence is low or evidence is preliminary, it must use hedged language:
  *"At the time of this report, X is considered the most likely explanation based on
  currently available evidence."*
- It must never state uncertain conclusions as facts.

This constraint is embedded in the system prompt for every generation and every delta update,
making it consistent regardless of which model or version is used.

---

## Where AI Content Appears in the PDF

The AI generates a **single narrative text** per report (stored as `ai_raw_content` in the
database). For this text to appear in the rendered PDF, the report template must contain a
**Text Block** with the field set to `ai.executive_summary`.

In the template builder, add a **Text Block** and set its **Field** to `AI Executive Summary`.
Place it wherever it makes sense for your audience — typically after the cover page for
Management, or after the IOC table for Technical.

> The `AI Strategy Summary` block in the builder is a placeholder and does not currently
> render AI content. Use **Text Block → ai.executive_summary** instead.

---

## Version Tracking in the UI

In the Reports tab of any incident, each report row shows:

- A **vN** badge (e.g. `v1`, `v2`, `v3`) indicating the version number, scoped per template.
- An **AI** chip on rows generated by the AI agent.
- A status indicator: generating, ready, or failed.

A persistent banner above the report list shows the live AI agent state:

| Banner | Meaning |
|---|---|
| Pulsing indicator — "AI is generating a new report version…" | One or more AI reports are in progress |
| Green check — "AI report is current. Last generated: [time] (vN)" | Latest AI report is ready |
| Red warning — "AI report generation failed. It will retry on the next incident update." | Latest AI report failed |

---

## Celery Queue Isolation

AI report generation runs on a dedicated Celery queue (`ai`), separate from the standard
reports queue. This means a slow Ollama call (typically 30–120 seconds) never blocks a
manual PDF export or SharePoint sync triggered at the same time.

---

## Infrastructure

The Ollama service is included in the Docker Compose configuration as an optional profile:

```bash
# Start IRDoc with Ollama
docker compose --profile ai up -d

# Without --profile ai, Ollama is absent and AI features are silently disabled
docker compose up -d
```

Models are not pre-installed. After first launch, pull your chosen model:

```bash
docker compose --profile ai exec ollama ollama pull llama3.2
```

Model files persist in a named Docker volume (`ollama_data`) between restarts.

The `ollama_base_url` in the AI config defaults to `http://ollama:11434`, which resolves
correctly inside the Compose network. Advanced users can point this at an external Ollama
instance (e.g. `http://host.docker.internal:11434` for native Ollama on macOS/Windows).

---

## Limitations

- **One narrative per report.** The AI generates a single text output per report generation.
  Section-level regeneration (e.g. regenerating only the IOC analysis section) is not yet
  supported.
- **Context window.** Very large incidents (many timeline entries, many IOCs) may exceed
  the model's context window. Use the **Max Timeline Events** setting to control prompt size.
  IOCs are capped at 50 items in the prompt regardless of this setting.
- **Model quality varies.** Smaller models (≤7B parameters) produce lower-quality narratives.
  `llama3.2` (3B) is the default and works for most cases. For higher quality, use
  `llama3.1:8b`, `mistral`, or `qwen2.5:7b` and update the model name in AI config.
- **No cloud AI.** Only Ollama (local) is supported. This is intentional — incident data
  is sensitive and should not leave your network.
