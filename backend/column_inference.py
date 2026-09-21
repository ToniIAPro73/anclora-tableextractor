"""Small-LLM column-name inference (GPT-5.4-mini via Emergent Universal Key).

STRICT SCOPE: the model is used ONLY to propose human-readable column header
names from the detected content. It NEVER produces, alters, or generates the
extracted cell data itself.
"""
import json
import logging
import os
import re

from emergentintegrations.llm.chat import LlmChat, UserMessage

logger = logging.getLogger(__name__)

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY")


def _fallback_names(header_row, ncols):
    names = []
    for c in range(ncols):
        raw = (header_row[c]["value"].strip() if header_row and c < len(header_row) else "")
        names.append(raw or f"Columna {c + 1}")
    return names


async def infer_column_names(rows, ncols, lang="es"):
    """rows: list of raw rows (list of cell dicts). Returns list[str] of length ncols."""
    if ncols == 0:
        return []
    header_row = rows[0] if rows else None
    sample = rows[:6]
    grid = [[(c["value"] if c else "") for c in row] for row in sample]

    if not EMERGENT_LLM_KEY:
        return _fallback_names(header_row, ncols)

    lang_instr = "en español" if lang == "es" else "in English"
    system = (
        "You are a data schema assistant. Given the first rows of a table extracted "
        "from a PDF, propose concise, human-readable column header names. "
        "You MUST NOT invent, modify or output any cell data. Return ONLY a JSON "
        f"array of exactly {ncols} short column names {lang_instr}."
    )
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id="col-infer",
            system_message=system,
        ).with_model("openai", "gpt-5.4-mini")
        msg = UserMessage(text=f"Table sample rows (JSON):\n{json.dumps(grid, ensure_ascii=False)}\n\nReturn a JSON array of {ncols} column names.")
        resp = await chat.send_message(msg)
        text = resp if isinstance(resp, str) else str(resp)
        m = re.search(r"\[.*\]", text, re.DOTALL)
        if m:
            names = json.loads(m.group(0))
            names = [str(n).strip() for n in names][:ncols]
            while len(names) < ncols:
                names.append(f"Columna {len(names) + 1}")
            return names
    except Exception as e:  # pragma: no cover
        logger.warning(f"Column inference LLM failed: {e}")
    return _fallback_names(header_row, ncols)
