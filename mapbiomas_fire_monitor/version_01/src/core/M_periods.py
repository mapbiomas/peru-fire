"""Normalization helpers for sample period columns."""


def normalize_period(value):
    """Return YYYY or YYYY_MM as text, accepting numeric CSV values."""
    if value is None:
        return ''
    text = str(value).strip()
    if text.lower() in {'', 'nan', 'nat', 'none', '<na>'}:
        return ''
    if text.endswith('.0') and text[:-2].isdigit():
        text = text[:-2]
    if text.isdigit() and len(text) == 6:
        return f"{text[:4]}_{text[4:]}"
    return text


def period_year(value):
    """Return the integer year from a period value, or None."""
    token = normalize_period(value).split('_')[0]
    try:
        return int(float(token))
    except (TypeError, ValueError):
        return None
