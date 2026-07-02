# AI Configuration

> **Admin role required.**

IRDoc can generate AI-powered executive summaries and remediation recommendations for incidents using a locally-run language model via Ollama. All AI processing happens on your own infrastructure — no data is sent to external AI APIs. Go to **Admin → AI**.

---

## Prerequisites

- [Ollama](https://ollama.ai) installed and running on a host accessible from the IRDoc backend container
- At least one model pulled in Ollama (recommended: `llama3`, `mistral`, or `phi3`)
- The Ollama API endpoint reachable from the IRDoc backend container

---

## Configuration

| Field | Description | Example |
|---|---|---|
| Ollama Base URL | Full URL to the Ollama API | `http://ollama-host:11434` |
| Model Name | Ollama model to use for generation | `llama3` |
| Debounce (seconds) | How long to wait after an incident change before triggering auto-generation | `30` |
| Max timeline events | Maximum number of timeline entries fed into the prompt | `50` |

Click **Test Connection** to verify IRDoc can reach Ollama and that the specified model is available.

---

## What AI generates

- **Executive Summary:** A concise overview of the incident suitable for non-technical stakeholders. Generated from the incident metadata, timeline entries, and IOCs.
- **Recommendations:** Remediation and prevention steps based on the incident's attack vectors, affected assets, and IOC types.

Both fields appear in the incident's **Summary** tab. Analysts can edit the generated text after generation.

---

## Triggering generation

- **Manual:** Open the Summary tab in any incident and click **Generate with AI**
- **Automatic:** If Debounce is set, generation is queued automatically after each significant incident update (new timeline entry, IOC change, status change) with the configured delay

---

## Disabling AI

Clear the **Ollama Base URL** field and save. The **Generate with AI** button is hidden from the Summary tab when AI is not configured.

---

## Privacy note

- Incident data (title, timeline entries, IOC values) is sent to your Ollama instance
- Ollama itself does not send data externally when using a locally-pulled model
- Ensure your Ollama host is network-isolated appropriately for your security requirements
