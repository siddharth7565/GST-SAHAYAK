"""Scrape selected CGST / IGST sections from AdvocateKhoj into sub-section-aware chunks.

Usage (run from the backend folder, venv active):
    python scrape_gst.py download   # fetch HTML into raw/ (polite, skips files already saved)
    python scrape_gst.py parse      # build corpus.json + review.txt from raw/
    python scrape_gst.py debug igst 8   # show raw HTML tail of one saved page

Edit ACTS below to change which sections are included. Section titles are read from
the pages themselves, so review.txt will show immediately if a number is wrong.

v2 changes: <br>-glued footnotes are split out and dropped, stray [ ] and * markers are
removed, and chunks are cut at sub-section boundaries so labels read like
"[CGST Act 2017, Section 22(1) - Persons liable for registration]".
"""
import json
import re
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE = "https://www.advocatekhoj.com/library/bareacts"
HEADERS = {"User-Agent": "GSTSahayak-student-project"}
RAW = Path("raw")
MAX_CHARS = 800  # body characters per chunk (MiniLM only embeds roughly the first 256 tokens)
DEFINITION_STYLE_MIN_GROUPS = 25  # sections with more sub-sections than this get one chunk per sub-section

ACTS = {
    "cgst": {
        "folder": "centralgstact",
        "name": "CGST Act 2017",
        "sections": ["2", "7", "9", "13", "15", "16", "17", "18", "22", "23", "24", "25", "31", "37", "39"],
    },
    "igst": {
        "folder": "integratedgst2017",
        "name": "IGST Act 2017",
        "sections": ["2", "5", "7", "8", "12", "13", "16"],
    },
}


def page_url(act_key, section):
    return f"{BASE}/{ACTS[act_key]['folder']}/{section}.php"


# ---------------------------------------------------------------- download
def download():
    for key, act in ACTS.items():
        (RAW / key).mkdir(parents=True, exist_ok=True)
        for sec in act["sections"]:
            path = RAW / key / f"{sec}.html"
            if path.exists():
                continue
            url = page_url(key, sec)
            r = requests.get(url, headers=HEADERS, timeout=30)
            print(r.status_code, url)
            if r.status_code == 200:
                path.write_text(r.text, encoding="utf-8")
            time.sleep(1.5)


# ------------------------------------------------------------------- parse
HEAD_WITH_DOT_DASH = re.compile(r"^(\d+[A-Za-z]?)\.\s*(.+?)\.\s*[-–—]\s*(.*)$", re.S)
HEAD_PLAIN = re.compile(r"^(\d+[A-Za-z]?)\.\s*(.+?)[\s.\-–—]*$", re.S)
FOOTNOTE_START = re.compile(r"^\d{1,3}\s*\.\s*\S")
FOOTNOTE_HINT = re.compile(
    r"w\.e\.f|\bAct,?\s+\d+\s+of\s+\d{4}|\b(?:ins|subs|omitted|inserted|substituted|added)\b\.?\s+by\b|\bNotification\b|\bOrder No",
    re.I,
)
EXPL_START = re.compile(r"^Explanation\b")
MARKER = re.compile(r"(?<![\w])\d{1,3}\[")
SUB_START = re.compile(r"^\((\d+[A-Za-z]?)\)\s")


def parse_heading(text):
    m = HEAD_WITH_DOT_DASH.match(text)
    if m:
        return m.group(1), m.group(2).strip(), m.group(3).strip()
    m = HEAD_PLAIN.match(text)
    if m:
        return m.group(1), m.group(2).strip(), ""
    return None


def clean_paragraphs(paragraphs):
    """Remove amendment markers ('1[' ... ']'), asterisk footnote marks and bare-number lines."""
    out = []
    for p in paragraphs:
        p = MARKER.sub("", p)
        p = p.replace("[", "").replace("]", "").replace("*", "").replace("\xa0", " ")
        p = re.sub(r"\s+", " ", p).strip()
        if p and not re.fullmatch(r"\d{1,3}", p):
            out.append(p)
    return out


def parse_section(html):
    """Return dict(number, title, paragraphs, dropped) or None if the page layout is not recognised."""
    soup = BeautifulSoup(html, "html.parser")
    box = soup.select_one("div.bareacts_contentarea")
    if box is None:
        return None
    items = []
    for el in box.find_all(["p", "li"]):
        for br in el.find_all("br"):
            br.replace_with("\u0001")
        bold = "font-bold" in (el.get("class") or [])
        for line in el.get_text(" ", strip=True).split("\u0001"):
            line = re.sub(r"[\u200b-\u200d\ufeff]", "", line).replace("\xa0", " ").strip()
            if line:
                items.append((bold, line))

    head = None
    start = None
    for i, (bold, text) in enumerate(items):
        if bold:
            parsed = parse_heading(text)
            if parsed:
                head, start = parsed, i
                break
    if head is None:
        return None

    number, title, rest = head
    lines = [text for _, text in items[start + 1:]]
    cut = len(lines)
    for i, text in enumerate(lines):  # first line that looks like "3. Subs. by Act 31 of 2018..."
        if FOOTNOTE_START.match(text) and FOOTNOTE_HINT.search(text):
            cut = i
            break
    while 0 < cut < len(lines) and FOOTNOTE_START.match(lines[cut - 1]):  # earlier numbered notes
        cut -= 1
    body = ([rest] if rest else []) + lines[:cut]
    dropped = lines[cut:]
    return {
        "number": number,
        "title": title,
        "paragraphs": clean_paragraphs(body),
        "dropped": dropped,
    }


# --------------------------------------------------------------- chunking
def split_long_paragraph(p, limit):
    sentences = re.split(r"(?<=[.;:])\s+", p)
    parts, cur = [], ""
    for s in sentences:
        if cur and len(cur) + len(s) + 1 > limit:
            parts.append(cur)
            cur = s
        else:
            cur = f"{cur} {s}".strip()
    if cur:
        parts.append(cur)
    return parts


def pack_paragraphs(paragraphs, limit=MAX_CHARS):
    if len("\n".join(paragraphs)) <= limit:
        return ["\n".join(paragraphs)]
    units = []
    for p in paragraphs:
        units.extend(split_long_paragraph(p, limit) if len(p) > limit else [p])
    pieces, cur = [], ""
    for u in units:
        if cur and len(cur) + len(u) + 1 > limit:
            pieces.append(cur)
            cur = u
        else:
            cur = f"{cur}\n{u}".strip()
    if cur:
        pieces.append(cur)
    return pieces


def split_subsections(paragraphs):
    """Group paragraphs by top-level sub-section '(1)', '(2)'...; an Explanation becomes its own group
    keyed '<previous sub-section>|E' so it is cited as e.g. 'Section 22(1) Explanation'."""
    groups = []  # each: [key_or_None, [paragraphs]]
    last_num = None
    for p in paragraphs:
        m = SUB_START.match(p)
        if m:
            last_num = m.group(1)
            if len(groups) == 1 and groups[0][0] is None:  # preamble belongs with the first sub-section
                groups[0][0] = last_num
                groups[0][1].append(p)
            else:
                groups.append([last_num, [p]])
        elif EXPL_START.match(p) and groups:
            groups.append([f"{last_num or ''}|E", [p]])
        elif groups:
            groups[-1][1].append(p)
        else:
            groups.append([None, [p]])
    return groups


def label_range(subs):
    subs = [s for s in subs if s]
    if not subs:
        return ""

    def fmt(s):
        if s.endswith("|E"):
            base = s[:-2]
            return f"({base}) Explanation" if base else "Explanation"
        return f"({s})"

    out = fmt(subs[0]) if subs[0] == subs[-1] else f"{fmt(subs[0])}-{fmt(subs[-1])}"
    return f" {out}" if out == "Explanation" else out


def make_pieces(paragraphs, limit=MAX_CHARS):
    """Return list of (sub_numbers, text, part) where part is (i, n) when one sub-section was split."""
    groups = split_subsections(paragraphs)
    merge = len(groups) <= DEFINITION_STYLE_MIN_GROUPS
    pieces = []
    cur = {"subs": [], "text": ""}

    def flush():
        if cur["text"]:
            pieces.append((cur["subs"], cur["text"], None))
        cur["subs"], cur["text"] = [], ""

    for sub, paras in groups:
        gtext = "\n".join(paras)
        isolated = bool(sub) and sub.endswith("|E")
        if len(gtext) > limit:
            flush()
            parts = pack_paragraphs(paras, limit)
            for i, t in enumerate(parts, start=1):
                pieces.append(([sub], t, (i, len(parts)) if len(parts) > 1 else None))
        elif merge and not isolated and cur["text"] and len(cur["text"]) + len(gtext) + 1 <= limit:
            cur["text"] += "\n" + gtext
            cur["subs"].append(sub)
        else:
            flush()
            cur["text"], cur["subs"] = gtext, [sub]
            if isolated:
                flush()
    flush()
    return pieces


def build_chunks(act_key, section_data, url):
    act_name = ACTS[act_key]["name"]
    num, title = section_data["number"], section_data["title"]
    chunks = []
    for i, (subs, text, part) in enumerate(make_pieces(section_data["paragraphs"]), start=1):
        rng = label_range(subs)
        part_s = f", part {part[0]}/{part[1]}" if part else ""
        label = f"[{act_name}, Section {num}{rng}{part_s} - {title}]"
        chunks.append({
            "act": act_name,
            "act_key": act_key,
            "section": num,
            "sub": rng,
            "title": title,
            "chunk_id": f"{act_key}_s{num.lower()}_c{i}",
            "text": f"{label}\n{text}",
            "source_url": url,
        })
    return chunks


def parse_all():
    corpus, review = [], []
    for key, act in ACTS.items():
        for sec in act["sections"]:
            path = RAW / key / f"{sec}.html"
            if not path.exists():
                review.append(f"[MISSING FILE] {key} {sec}")
                continue
            data = parse_section(path.read_text(encoding="utf-8"))
            if data is None:
                review.append(f"[PARSE FAILED] {key} {sec}: layout not recognised")
                continue
            if data["number"].lower() != sec.lower():
                review.append(f"[NUMBER MISMATCH] {key} {sec}: page says section {data['number']}")
            chunks = build_chunks(key, data, page_url(key, sec))
            corpus.extend(chunks)
            body = "\n".join(data["paragraphs"])
            labels = [c["text"].split("\n", 1)[0] for c in chunks]
            shown = labels[:6] + (["..."] if len(labels) > 6 else [])
            review.append(
                f"--- {act['name']} s.{data['number']} '{data['title']}' | "
                f"{len(data['paragraphs'])} paras | {len(body)} chars | {len(chunks)} chunk(s) | "
                f"{len(data['dropped'])} footnote lines dropped\n"
                f"  START: {body[:160]!r}\n  END:   {body[-160:]!r}\n"
                f"  FIRST DROPPED: {(data['dropped'][0][:120] if data['dropped'] else '(none)')!r}\n"
                f"  LABELS: {' | '.join(shown)}"
            )
    Path("corpus.json").write_text(json.dumps(corpus, ensure_ascii=False, indent=2), encoding="utf-8")
    Path("review.txt").write_text("\n".join(review), encoding="utf-8")
    print(f"{len(corpus)} chunks written to corpus.json; see review.txt")


def debug(act_key, section):
    """Print the raw HTML of the last 8 text elements of one saved page (to inspect footnote markup)."""
    html = (RAW / act_key / f"{section}.html").read_text(encoding="utf-8")
    box = BeautifulSoup(html, "html.parser").select_one("div.bareacts_contentarea")
    for el in box.find_all(["p", "li"])[-8:]:
        print(el.name, el.get("class"), repr(str(el)[:300]))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "download":
        download()
    elif cmd == "parse":
        parse_all()
    elif cmd == "debug" and len(sys.argv) == 4:
        debug(sys.argv[2], sys.argv[3])
    else:
        print(__doc__)