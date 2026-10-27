"""Citation helpers for GST Sahayak.

Retrieved chunks are shown to the LLM as numbered sources ([S1], [S2], ...). The model must
cite those tags after every legal statement. This module builds the numbered sources and
checks, on the server, which tags in an answer are real (point at a retrieved chunk) and
which are invented.
"""
import re
from typing import Dict, List, Optional, Set

REFUSAL_MESSAGE = (
    "I could not find sufficient supporting evidence in the available GST documents to answer this question."
)
_REFUSAL_MARKER = "could not find sufficient supporting evidence"

_BRACKET_GROUP = re.compile(r"\[([^\[\]]{1,60})\]")
_TAG_ONLY = re.compile(r"(?:\s*S\s*\d+\s*(?:,|;|&|and)?)+\s*", re.IGNORECASE)
_TAG_NUM = re.compile(r"S\s*(\d+)", re.IGNORECASE)


def split_label(chunk: dict):
    """Return (label, body) for a chunk. The label is the bracketed first line written by the
    scraper, e.g. 'CGST Act 2017, Section 22(1) - Persons liable for registration'."""
    text = (chunk.get("text") or "").strip()
    first, _, rest = text.partition("\n")
    first = first.strip()
    if first.startswith("[") and "]" in first:
        label = first[1:first.rfind("]")].strip()
        return label, rest.strip()
    label = chunk.get("citation_label") or chunk.get("chunk_id") or "source"
    return label, text


def short_act(act: Optional[str]) -> str:
    return (act or "?").split()[0].upper()


def section_key(item: dict) -> str:
    """'CGST 22' style key from a chunk/source dict that has 'act' and 'section'."""
    return f"{short_act(item.get('act'))} {item.get('section') or '?'}"


def build_sources(chunks: List[dict]) -> List[dict]:
    sources = []
    for idx, chunk in enumerate(chunks, start=1):
        label, body = split_label(chunk)
        sources.append({
            "tag": f"S{idx}",
            "index": idx,
            "chunk_id": chunk.get("chunk_id"),
            "label": label,
            "citation_label": chunk.get("citation_label") or label,
            "act": chunk.get("act"),
            "section": chunk.get("section"),
            "sub": chunk.get("sub"),
            "source_url": chunk.get("source_url"),
            "text": body,
        })
    return sources


def format_context(sources: List[dict]) -> str:
    return "\n\n".join(f"[{s['tag']}] {s['label']}\n{s['text']}" for s in sources)


def is_refusal(answer: Optional[str]) -> bool:
    return bool(answer) and _REFUSAL_MARKER in answer.lower()


def find_tags(answer: str) -> List[str]:
    """All source tags used in an answer, in order of appearance (with repeats). Accepts
    [S1], [S1][S2], [S1, S2] and [S1; S2]."""
    tags = []
    for m in _BRACKET_GROUP.finditer(answer or ""):
        inner = m.group(1)
        if _TAG_ONLY.fullmatch(inner):
            tags.extend(f"S{n}" for n in _TAG_NUM.findall(inner))
    return tags


def strip_tags(answer: str) -> str:
    def repl(m):
        return "" if _TAG_ONLY.fullmatch(m.group(1)) else m.group(0)
    return _BRACKET_GROUP.sub(repl, answer or "")


def extract_citations(answer: Optional[str], sources: List[dict]) -> Dict:
    """Check an answer's citations against the sources it was given."""
    by_tag = {s["tag"]: s for s in sources}
    used = find_tags(answer or "")
    seen: Set[str] = set()
    citations, invalid = [], []
    for tag in used:
        if tag in seen:
            continue
        seen.add(tag)
        src = by_tag.get(tag)
        if src is None:
            invalid.append(tag)
            continue
        citations.append({
            "tag": tag,
            "chunk_id": src["chunk_id"],
            "citation_label": src["citation_label"],
            "label": src["label"],
            "source_url": src["source_url"],
            "excerpt": src["text"][:240],
        })
    refused = is_refusal(answer)
    cited_chunk_ids = [c["chunk_id"] for c in citations]
    cited_sections = sorted({section_key(by_tag[c["tag"]]) for c in citations})
    return {
        "citations": citations,
        "invalid_citations": invalid,
        "uncited_answer": (not refused) and bool(answer) and not citations,
        "refused": refused,
        "cited_chunk_ids": cited_chunk_ids,
        "cited_sections": cited_sections,
    }
