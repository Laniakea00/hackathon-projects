"""Shared text utilities for cleaning and chunking clinical protocol text.

Used by both the ingestion script and the bootstrap script.
"""

import re

# ── Text cleaning ─────────────────────────────────────────────────────────────

# Case-insensitive patterns that mark the start of "noise tails".
# Everything from the first match to EOF is dropped.
_NOISE_TAIL_RE = re.compile(
    r"("
    r"список использованной литературы"
    r"|использованная литература"
    r"|список литературы"
    r"|разработчики"
    r"|рецензенты"
    r")",
    flags=re.IGNORECASE,
)


def clean_text(text: str) -> str:
    """Remove bibliography / author sections and normalise whitespace.

    What is REMOVED (noise):
    - Anything after the first bibliography / author section header.

    What is PRESERVED:
    - Differential diagnosis tables (even if poorly formatted).
    - "NB!" notes – critical clinical signals.
    - ICD-10 codes mentioned in the body text.
    - Section headings (1.1, 2.3, …) that give the LLM structural context.
    """
    match = _NOISE_TAIL_RE.search(text)
    if match:
        text = text[: match.start()]

    # Collapse runs of 3+ blank lines → two (preserve paragraph breaks)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Strip trailing whitespace from each line
    text = re.sub(r"[ \t]+\n", "\n", text)
    # Collapse mid-line multiple spaces
    text = re.sub(r" {2,}", " ", text)

    return text.strip()


# ── Chunking ──────────────────────────────────────────────────────────────────

_DEFAULT_CHUNK_SIZE = 1000
_DEFAULT_OVERLAP = 200


def chunk_text(
    text: str,
    chunk_size: int = _DEFAULT_CHUNK_SIZE,
    overlap: int = _DEFAULT_OVERLAP,
) -> list[str]:
    """Split *text* into overlapping character-level chunks.

    The splitter first tries paragraph boundaries (\\n\\n), then sentence
    boundaries (``.!?``), then falls back to hard character cuts.
    Overlap is applied by prepending the tail of the previous chunk.
    """
    raw_chunks = _split_recursive(text, chunk_size)

    if overlap <= 0 or len(raw_chunks) <= 1:
        return raw_chunks

    # Prepend tail of the previous chunk to each chunk (except the first)
    overlapped: list[str] = [raw_chunks[0]]
    for i in range(1, len(raw_chunks)):
        prev_tail = raw_chunks[i - 1][-overlap:]
        overlapped.append(prev_tail + "\n\n" + raw_chunks[i])

    return overlapped


def _split_recursive(text: str, chunk_size: int) -> list[str]:
    """Recursively split text using progressively finer boundaries."""
    if len(text) <= chunk_size:
        return [text] if text.strip() else []

    # Try splitting on paragraph boundaries first
    for sep, joiner in [("\n\n", "\n\n"), ("\n", "\n"), (". ", ". ")]:
        parts = text.split(sep)
        if len(parts) <= 1:
            continue

        chunks: list[str] = []
        current: list[str] = []
        current_len: int = 0

        for part in parts:
            part_len = len(part)
            addition = part_len + len(sep) if current else part_len

            if current_len + addition <= chunk_size:
                current.append(part)
                current_len += addition
            else:
                if current:
                    chunks.append(joiner.join(current))
                # If a single part is still too big, recurse
                if part_len > chunk_size:
                    chunks.extend(_split_recursive(part, chunk_size))
                    current, current_len = [], 0
                else:
                    current, current_len = [part], part_len

        if current:
            chunks.append(joiner.join(current))

        return [c for c in chunks if c.strip()]

    # Hard cut as last resort
    return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]
