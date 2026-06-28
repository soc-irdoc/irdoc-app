"""
Provider-agnostic AI service.

Supports Anthropic (claude-sonnet-4-6), OpenAI, and Ollama (air-gapped local).

For Ollama (the only supported provider in this platform):
  - Provider reads config from the DB-backed AiConfig (base URL, model name).
  - get_ai_provider(ai_config) accepts an AiConfig ORM object.
  - Falls back to env-based config if no AiConfig is passed.

Usage:
    provider = get_ai_provider(ai_config)
    text = await provider.complete(system="...", user="...", max_tokens=800)
"""
from __future__ import annotations

import ipaddress
import logging
import socket
from typing import Protocol, runtime_checkable, TYPE_CHECKING
from urllib.parse import urlparse

from app.core.config import settings

if TYPE_CHECKING:
    from app.models.ai_config import AiConfig

logger = logging.getLogger(__name__)


def validate_ollama_url(url: str) -> None:
    """Validate Ollama base URL to prevent SSRF.

    Blocks loopback, private, link-local, multicast, and unspecified addresses
    by resolving the hostname to IPs and checking each one.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Ollama URL must use http or https scheme")
    host = (parsed.hostname or "").rstrip(".").lower()
    if not host:
        raise ValueError("Ollama URL must have a host")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        infos = socket.getaddrinfo(host, port)
    except socket.gaierror:
        raise ValueError("Ollama host does not resolve")
    for _fam, _type, _proto, _canon, sockaddr in infos:
        ip = ipaddress.ip_address(sockaddr[0])
        if (
            ip.is_loopback
            or ip.is_private
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_unspecified
            or ip.is_reserved
        ):
            raise ValueError(
                f"Ollama URL resolves to a disallowed address ({ip}). "
                "Only publicly routable addresses are permitted."
            )


@runtime_checkable
class AIProvider(Protocol):
    async def complete(self, system: str, user: str, max_tokens: int = 400) -> str: ...


class AnthropicProvider:
    """Uses claude-sonnet-4-6 by default. Respects AI_MODEL env var."""

    async def complete(self, system: str, user: str, max_tokens: int = 400) -> str:
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY, timeout=120.0)
        response = await client.messages.create(
            model=settings.AI_MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return response.content[0].text


class OpenAIProvider:
    async def complete(self, system: str, user: str, max_tokens: int = 400) -> str:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY, timeout=120.0)
        response = await client.chat.completions.create(
            model=settings.AI_MODEL,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content or ""


class OllamaProvider:
    """Local LLM for air-gapped deployments (llama3, mistral, qwen, etc.).

    Configured from DB (AiConfig) when available; falls back to env vars.
    """

    def __init__(self, base_url: str | None = None, model: str | None = None):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.AI_MODEL

    async def complete(self, system: str, user: str, max_tokens: int = 800) -> str:
        import httpx

        payload = {
            "model": self.model,
            "prompt": f"{system}\n\n{user}",
            "stream": False,
            "options": {"num_predict": max_tokens},
        }
        async with httpx.AsyncClient(timeout=300) as client:
            response = await client.post(f"{self.base_url}/api/generate", json=payload)
            response.raise_for_status()
            return response.json().get("response", "")


def get_ai_provider(ai_config: "AiConfig | None" = None) -> AIProvider:
    """
    Returns the active AI provider.

    If ai_config is provided and enabled, always returns OllamaProvider configured
    from the DB values. Otherwise falls back to env-based provider selection.
    """
    if ai_config is not None and ai_config.is_enabled:
        return OllamaProvider(
            base_url=ai_config.ollama_base_url,
            model=ai_config.model_name,
        )

    # Legacy env-based fallback (used by existing tasks that don't pass ai_config)
    providers = {
        "anthropic": AnthropicProvider,
        "openai": OpenAIProvider,
        "ollama": OllamaProvider,
    }
    provider_cls = providers.get(settings.AI_BACKEND, AnthropicProvider)
    return provider_cls()


# ─── Prompt builders ──────────────────────────────────────────────────────────

_AUDIENCE_SYSTEM: dict[str, str] = {
    "management": (
        "You are a senior incident response analyst writing a concise executive summary "
        "for a non-technical management audience. Focus on: what happened, what was affected, "
        "what was done, and current status. Write in 3-5 clear sentences. "
        "Use plain language — no technical jargon. Past tense for resolved items. "
        "Do not use bullet points. "
        "IMPORTANT: Use ONLY the evidence provided below. Do not introduce new facts. "
        "Do not speculate beyond what the data supports. "
        "Where evidence is preliminary or confidence is low, use hedged language such as: "
        "'At the time of this report, X is considered the most likely explanation based on "
        "currently available evidence.' Never state uncertain conclusions as facts."
    ),
    "analyst": (
        "You are a senior technical incident response analyst writing a detailed technical "
        "analysis for your IR team. Focus on: attack vectors, indicators of compromise (IOC types "
        "and values), affected systems, TTPs observed, technical timeline, and remediation steps. "
        "Be specific — reference IOC values, entry types, and technical findings from the data. "
        "Use numbered sections if helpful. Past tense for resolved items. "
        "IMPORTANT: Use ONLY the evidence provided below. Do not introduce new facts. "
        "Do not speculate beyond what the data supports. "
        "Where evidence is preliminary, use hedged language: 'Based on currently available evidence, "
        "X is the most likely explanation.' Flag any gaps in the evidence chain explicitly."
    ),
    "legal": (
        "You are a senior incident response analyst writing a factual incident narrative for "
        "legal counsel and compliance review. Focus on: a precise chronological timeline of events, "
        "the chain of evidence, who did what and when, affected data or systems, and any regulatory "
        "implications suggested by the evidence. "
        "Write in plain, precise language suitable for legal proceedings. Avoid technical jargon. "
        "Be especially conservative with speculation — every claim must be grounded in the provided "
        "evidence. Use explicit hedges: 'Based on currently available evidence...', "
        "'It has not yet been determined whether...'. "
        "IMPORTANT: Use ONLY the evidence provided below. Do not introduce new facts."
    ),
}

_DEFAULT_SYSTEM = _AUDIENCE_SYSTEM["management"]


def build_executive_summary_prompt(
    payload, max_timeline_events: int = 20, audience: str | None = None
) -> tuple[str, str]:
    system = _AUDIENCE_SYSTEM.get(audience or "", _DEFAULT_SYSTEM)

    # Cap timeline events to avoid token overflow; annotate if truncated
    entries = payload.entries[:max_timeline_events]
    truncated = len(payload.entries) > max_timeline_events
    timeline_lines = "\n".join(
        f"[{e.entry_type.upper()}] {e.description[:200]}" for e in entries
    )
    if truncated:
        timeline_lines += f"\n… and {len(payload.entries) - max_timeline_events} more events (not shown)"

    # Cap IOC list at 50 items
    ioc_active = payload.iocs_by_status.get("active", [])
    ioc_note = f"{payload.ioc_count} total ({len(ioc_active)} active)"
    if payload.ioc_count > 50:
        ioc_note += f" — showing first 50 of {payload.ioc_count}"

    user = (
        f"Incident: {payload.incident.title}\n"
        f"Severity: {payload.severity_label}\n"
        f"Duration: {payload.duration_str}\n"
        f"Affected users: {payload.incident.affected_users}\n"
        f"Status: {payload.status_label}\n\n"
        f"Timeline summary ({min(len(payload.entries), max_timeline_events)} events):\n{timeline_lines}\n\n"
        f"IOCs: {ioc_note}\n"
        f"Task completion: {payload.task_completion_pct}%\n\n"
        "Write the executive summary:"
    )
    return system, user


def build_delta_report_prompt(
    payload,
    previous_narrative: str | None,
    max_timeline_events: int = 20,
    audience: str | None = None,
) -> tuple[str, str]:
    """
    Builds a delta-aware prompt for versioned AI report generation.

    If previous_narrative is None: full first-generation prompt (v1).
    If previous_narrative is provided: delta prompt — AI is instructed to
    keep stable sections unchanged and only update what new evidence requires.
    audience maps to ReportTemplate.destination (management/analyst/legal/custom).
    """
    if previous_narrative is None:
        return build_executive_summary_prompt(payload, max_timeline_events, audience)

    base_persona = _AUDIENCE_SYSTEM.get(audience or "", _DEFAULT_SYSTEM)

    system = (
        f"{base_persona}\n\n"
        "You are now UPDATING an existing report. You will receive the PREVIOUS report narrative "
        "and the CURRENT incident data. Your task:\n"
        "1. Keep all sections that have NOT changed EXACTLY as they were — same wording, same structure.\n"
        "2. Update ONLY the sections affected by new evidence, timeline events, or status changes.\n"
        "3. If any statement in the previous report now contradicts the current evidence, "
        "flag it explicitly: 'NOTE: Previous assessment [quote] is superseded by [new finding].'\n"
        "4. Where evidence is preliminary, use hedged language: 'At the time of this report, "
        "X is considered the most likely explanation based on currently available evidence.'\n"
        "5. Use ONLY the provided evidence. Do not introduce new facts. Do not speculate."
    )

    entries = payload.entries[:max_timeline_events]
    truncated = len(payload.entries) > max_timeline_events
    timeline_lines = "\n".join(
        f"[{e.entry_type.upper()}] {e.description[:200]}" for e in entries
    )
    if truncated:
        timeline_lines += f"\n… and {len(payload.entries) - max_timeline_events} more events (not shown)"

    ioc_active = payload.iocs_by_status.get("active", [])

    user = (
        f"--- PREVIOUS REPORT NARRATIVE ---\n{previous_narrative}\n"
        f"--- END PREVIOUS REPORT ---\n\n"
        f"--- CURRENT INCIDENT DATA ---\n"
        f"Incident: {payload.incident.title}\n"
        f"Severity: {payload.severity_label}\n"
        f"Duration: {payload.duration_str}\n"
        f"Affected users: {payload.incident.affected_users}\n"
        f"Status: {payload.status_label}\n\n"
        f"Timeline ({min(len(payload.entries), max_timeline_events)} events):\n{timeline_lines}\n\n"
        f"IOCs: {payload.ioc_count} total ({len(ioc_active)} active)\n"
        f"Task completion: {payload.task_completion_pct}%\n"
        f"--- END CURRENT DATA ---\n\n"
        "Write the updated report narrative. Preserve unchanged sections verbatim. "
        "Flag any contradictions with the previous version."
    )
    return system, user


def build_recommendations_prompt(payload, max_timeline_events: int = 15) -> tuple[str, str]:
    system = (
        "You are a senior incident response analyst writing post-incident recommendations. "
        "Provide 3-5 specific, actionable technical recommendations to prevent recurrence. "
        "Be concrete — reference the specific attack vector and findings. "
        "Format as a numbered list."
    )

    attack_vector = ", ".join(payload.incident.attack_vector or ["Unknown"])
    ioc_types = list({i.ioc_type for i in payload.iocs})

    entries = payload.entries[:max_timeline_events]
    timeline_lines = "\n".join(
        f"[{e.entry_type.upper()}] {e.description[:200]}" for e in entries
    )

    user = (
        f"Incident: {payload.incident.title}\n"
        f"Severity: {payload.severity_label}\n"
        f"Attack vector: {attack_vector}\n"
        f"IOC types observed: {', '.join(ioc_types) or 'None'}\n\n"
        f"Key timeline events:\n{timeline_lines}\n\n"
        "Write 3-5 specific recommendations to prevent recurrence:"
    )
    return system, user
