"""Optional OpenAI-compatible column-name inference with deterministic fallback."""

from __future__ import annotations

import json
import logging
import re

from config import get_settings

logger = logging.getLogger(__name__)


def _fallback_names(header_row, ncols):
    names = []
    for c in range(ncols):
        raw = (
            header_row[c]["value"].strip() if header_row and c < len(header_row) else ""
        )
        names.append(raw or f"Columna {c + 1}")
    return names


def _normalize_names(value, ncols, fallback):
    if isinstance(value, str):
        match = re.search(r"\[.*\]", value, re.DOTALL)
        if not match:
            return fallback
        try:
            value = json.loads(match.group(0))
        except json.JSONDecodeError:
            return fallback
    if not isinstance(value, list) or len(value) != ncols:
        return fallback
    names = [str(name).strip() for name in value]
    return names if all(names) else fallback


async def _provider_names(grid, ncols, lang, fallback):
    settings = get_settings()
    if settings.llm_provider.lower() in {"", "disabled", "none"} or not settings.llm_api_key:
        return fallback
    if settings.llm_provider.lower() != "openai":
        logger.warning("Unsupported LLM provider %r; using deterministic fallback", settings.llm_provider)
        return fallback

    from openai import AsyncOpenAI

    client_kwargs = {"api_key": settings.llm_api_key}
    if settings.llm_base_url:
        client_kwargs["base_url"] = settings.llm_base_url
    client = AsyncOpenAI(**client_kwargs)
    try:
        language = "en inglés" if lang == "en" else "en español"
        response = await client.chat.completions.create(
            model=settings.llm_model,
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You propose concise human-readable table column names. "
                        f"Return ONLY a JSON array of exactly {ncols} names {language}. "
                        "Never modify or return cell data."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Table sample rows (JSON): {json.dumps(grid, ensure_ascii=False)}\n"
                        f"Return exactly {ncols} column names."
                    ),
                },
            ],
        )
        content = response.choices[0].message.content if response.choices else None
        return _normalize_names(content, ncols, fallback)
    except Exception as exc:  # provider failures must not block extraction
        logger.warning("Column inference provider failed: %s", exc)
        return fallback
    finally:
        await client.close()


async def infer_column_names(rows, ncols, lang="es"):
    """Return exactly ncols names without mutating the extracted cell grid."""
    if ncols == 0:
        return []
    header_row = rows[0] if rows else None
    fallback = _fallback_names(header_row, ncols)
    sample = rows[:6]
    grid = [[(cell["value"] if cell else "") for cell in row] for row in sample]
    return await _provider_names(grid, ncols, lang, fallback)
