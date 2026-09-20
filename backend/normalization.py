"""Deterministic normalization layer (NO LLM).

Handles date formats, decimal/thousand separators, currency & unit stripping.
Produces a normalized value plus a normalization-confidence in [0,1] that is
combined with the extraction confidence to yield the final cell score.
"""
import re
from datetime import datetime

CURRENCY_SYMBOLS = "€$£¥₹"
UNIT_TOKENS = ("kg", "km", "cm", "mm", "m", "g", "l", "ml", "%", "pcs", "u", "uds")

_DATE_FORMATS = [
    "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%d.%m.%Y",
    "%Y/%m/%d", "%d/%m/%y", "%m/%d/%y", "%d %b %Y", "%d %B %Y",
    "%b %d, %Y", "%B %d, %Y", "%d-%b-%Y", "%Y%m%d",
]


def _clean(raw):
    return (raw or "").strip()


def looks_like_date(s: str) -> bool:
    s = s.strip()
    return bool(re.search(r"\d", s)) and bool(
        re.search(r"[/\-.]", s) or re.search(r"\b\d{4}\b", s)
    ) and len(s) <= 24


def looks_like_number(s: str) -> bool:
    s = s.strip()
    if not s:
        return False
    body = s
    for ch in CURRENCY_SYMBOLS:
        body = body.replace(ch, "")
    body = body.strip()
    for u in UNIT_TOKENS:
        if body.lower().endswith(u):
            body = body[: -len(u)].strip()
    return bool(re.fullmatch(r"[+-]?[\d.,\s]+", body)) and any(c.isdigit() for c in body)


def normalize_date(s: str):
    s = s.strip()
    for fmt in _DATE_FORMATS:
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%Y-%m-%d"), 1.0
        except ValueError:
            continue
    # partial: only year
    m = re.fullmatch(r"(\d{4})", s)
    if m:
        return f"{m.group(1)}-01-01", 0.6
    return s, 0.5


def normalize_number(s: str):
    original = s.strip()
    body = original
    for ch in CURRENCY_SYMBOLS:
        body = body.replace(ch, "")
    body = body.strip()
    matched_unit = None
    for u in sorted(UNIT_TOKENS, key=len, reverse=True):
        if body.lower().endswith(u):
            matched_unit = u
            body = body[: -len(u)].strip()
            break
    body = body.replace(" ", "")
    neg = body.startswith("-") or (body.startswith("(") and body.endswith(")"))
    body = body.strip("()").lstrip("+-")

    has_comma = "," in body
    has_dot = "." in body
    conf = 1.0
    try:
        if has_comma and has_dot:
            # last separator is the decimal one
            if body.rfind(",") > body.rfind("."):
                body = body.replace(".", "").replace(",", ".")
            else:
                body = body.replace(",", "")
        elif has_comma:
            # comma could be decimal (es) or thousands separator
            groups = body.split(",")
            dec = groups[-1]
            if len(groups) > 2 and all(len(g) == 3 for g in groups[1:]):
                body = body.replace(",", "")  # 1,234,567 -> thousands
            elif len(groups) == 2 and len(dec) == 3 and len(groups[0]) <= 3:
                body = body.replace(",", "")  # 1,234 -> thousands (ambiguous)
                conf = 0.85
            else:
                body = body.replace(",", ".")  # decimal comma (es)
        # dot only -> assume decimal / thousands where 3-digit groups
        elif has_dot:
            parts = body.split(".")
            if len(parts) > 2 or (len(parts) == 2 and len(parts[1]) == 3 and len(parts[0]) <= 3):
                # thousands grouping like 1.234
                if all(len(p) == 3 for p in parts[1:]):
                    body = body.replace(".", "")
                    conf = 0.85
        value = float(body)
        if neg:
            value = -value
        out = f"{value:g}"
        return out, conf
    except ValueError:
        return original, 0.5


def infer_column_type(values):
    """Deterministic column-type inference over sampled values."""
    non_empty = [v for v in values if _clean(v)]
    if not non_empty:
        return "text"
    dates = sum(1 for v in non_empty if looks_like_date(v))
    nums = sum(1 for v in non_empty if looks_like_number(v))
    n = len(non_empty)
    if dates / n >= 0.6:
        return "date"
    if nums / n >= 0.6:
        return "number"
    return "text"


def normalize_value(raw: str, col_type: str):
    """Returns (normalized_value, normalization_confidence)."""
    s = _clean(raw)
    if not s:
        return "", 0.5  # empty -> needs review
    if col_type == "date":
        if looks_like_date(s):
            return normalize_date(s)
        return s, 0.55
    if col_type == "number":
        if looks_like_number(s):
            return normalize_number(s)
        return s, 0.55
    return s, 1.0
