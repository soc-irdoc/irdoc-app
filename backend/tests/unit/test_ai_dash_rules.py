"""AI output must use plain hyphens: every provider adds the style rule to the
system prompt and normalises em/en dashes in what the model returns."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ai_service import OllamaProvider, normalize_dashes, with_style_rules

EM_DASH = chr(0x2014)
EN_DASH = chr(0x2013)
BOX_LINE = chr(0x2500)


def test_normalize_dashes_replaces_em_and_en_dashes():
    text = f"Contained at 14:02 {EM_DASH} hosts 1{EN_DASH}3 isolated"
    assert normalize_dashes(text) == "Contained at 14:02 - hosts 1-3 isolated"


def test_normalize_dashes_leaves_other_text_alone():
    text = f"Plain - hyphen, {BOX_LINE} box line, and no dashes"
    assert normalize_dashes(text) == text


def test_with_style_rules_appends_dash_rule():
    out = with_style_rules("You are an analyst.")
    assert out.startswith("You are an analyst.")
    assert "hyphen" in out and "em dashes" in out


@pytest.mark.asyncio
async def test_ollama_provider_sends_rule_and_normalises_output():
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json = MagicMock(return_value={"response": f"Phishing {EM_DASH} credentials reset"})
    client = MagicMock()
    client.post = AsyncMock(return_value=response)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=client):
        text = await OllamaProvider(base_url="http://ollama:11434", model="m").complete("SYS", "USER")

    assert text == "Phishing - credentials reset"
    sent_prompt = client.post.call_args.kwargs["json"]["prompt"]
    assert sent_prompt.startswith("SYS") and "em dashes" in sent_prompt and sent_prompt.endswith("USER")
