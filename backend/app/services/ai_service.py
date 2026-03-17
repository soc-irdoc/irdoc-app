"""
Provider-agnostic AI service.

Supports Anthropic (claude-sonnet-4-6), OpenAI, and Ollama (air-gapped).
The active provider is selected by AI_BACKEND env var.

Usage:
    provider = get_ai_provider()
    text = await provider.complete(system="...", user="...", max_tokens=400)
"""
from __future__ import annotations

import logging
from typing import Protocol, runtime_checkable

from app.core.config import settings

logger = logging.getLogger(__name__)


@runtime_checkable
class AIProvider(Protocol):
    async def complete(self, system: str, user: str, max_tokens: int = 400) -> str: ...


class AnthropicProvider:
    """Uses claude-sonnet-4-6 by default. Respects AI_MODEL env var."""

    async def complete(self, system: str, user: str, max_tokens: int = 400) -> str:
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
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

        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
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
    """Local LLM for air-gapped deployments. Supports llama3, mistral, etc."""

    async def complete(self, system: str, user: str, max_tokens: int = 400) -> str:
        import httpx

        payload = {
            "model": settings.AI_MODEL,
            "prompt": f"{system}\n\n{user}",
            "stream": False,
            "options": {"num_predict": max_tokens},
        }
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json=payload,
            )
            response.raise_for_status()
            return response.json().get("response", "")


def get_ai_provider() -> AIProvider:
    providers = {
        "anthropic": AnthropicProvider,
        "openai": OpenAIProvider,
        "ollama": OllamaProvider,
    }
    provider_cls = providers.get(settings.AI_BACKEND, AnthropicProvider)
    return provider_cls()


# ─── Prompt builders ─────────────────────────────────────────────────────────

def build_executive_summary_prompt(payload) -> tuple[str, str]:
    system = (
        "You are a senior incident response analyst writing a concise executive summary "
        "for a non-technical management audience. Focus on: what happened, what was affected, "
        "what was done, and current status. Write in 3-5 clear sentences. "
        "Use plain language. Past tense for resolved items. Do not use bullet points."
    )

    timeline_lines = "\n".join(
        f"[{e.entry_type.upper()}] {e.description[:200]}"
        for e in payload.entries[:20]
    )

    user = (
        f"Incident: {payload.incident.title}\n"
        f"Severity: {payload.severity_label}\n"
        f"Duration: {payload.duration_str}\n"
        f"Affected users: {payload.incident.affected_users}\n"
        f"Status: {payload.status_label}\n\n"
        f"Timeline summary (first 20 events):\n{timeline_lines}\n\n"
        f"IOCs: {payload.ioc_count} total "
        f"({len(payload.iocs_by_status.get('active', []))} active)\n"
        f"Task completion: {payload.task_completion_pct}%\n\n"
        "Write the executive summary:"
    )
    return system, user


def build_recommendations_prompt(payload) -> tuple[str, str]:
    system = (
        "You are a senior incident response analyst writing post-incident recommendations. "
        "Provide 3-5 specific, actionable technical recommendations to prevent recurrence. "
        "Be concrete — reference the specific attack vector and findings. "
        "Format as a numbered list."
    )

    attack_vector = ", ".join(payload.incident.attack_vector or ["Unknown"])
    ioc_types = list({i.ioc_type for i in payload.iocs})

    timeline_lines = "\n".join(
        f"[{e.entry_type.upper()}] {e.description[:200]}"
        for e in payload.entries[:15]
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
