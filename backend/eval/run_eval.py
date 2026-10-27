"""Mini evaluation harness for GST Sahayak.

Run from the backend folder with the venv active (Postgres running, corpus loaded):

    python eval/run_eval.py --retrieval-only                  # retrieval quality + threshold calibration, no LLM
    python eval/run_eval.py --dry-run                         # whole pipeline with a fake model, no API keys
    python eval/run_eval.py --providers gemini,mistral,grok   # real models, same retrieved context for each
    python eval/run_eval.py --providers gemini --only q01_flagship,q07_zero_rated

For every question in eval/queries.json it retrieves ONCE, then sends the SAME citation-anchored prompt to each
provider and records latency, citations (valid / invented), whether the cited sections are the expected ones,
refusal behaviour, a key-fact check and numbers that are not in the sources. Output goes to
eval/results/<timestamp>/ (results.json, results.csv, summary.md).

Honest limits: "unsupported numbers" and "invalid citations" are PROXIES for hallucination, not a measured
hallucination rate; factual correctness needs the manual_correctness column in results.csv filled by a human.
"""
import argparse
import concurrent.futures
import csv
import json
import os
import re
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(BACKEND / ".env")

from services.citations import REFUSAL_MESSAGE, extract_citations, is_refusal, section_key, strip_tags  # noqa: E402
from services.llm_providers import get_llm_provider  # noqa: E402
from services.rag_service import rag_service  # noqa: E402
from services.retrieval_service import retrieval_service  # noqa: E402

DEFAULT_PROVIDERS = "gemini,mistral,grok,ollama"
NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")


# ---------------------------------------------------------------- fake provider
class MockProvider:
    """Deterministic stand-in so the pipeline can be tested without API keys."""

    def __init__(self, refuse: bool = False):
        self._model_name = "mock-refuse" if refuse else "mock"
        self.refuse = refuse

    def is_configured(self):
        return True

    def generate_response(self, prompt: str) -> str:
        if self.refuse:
            return REFUSAL_MESSAGE
        tags = re.findall(r"^\[(S\d+)\]", prompt, flags=re.MULTILINE)
        cites = "".join(f"[{t}]" for t in tags[:2])
        return f"Based on the provided sources, the relevant provisions are summarised here {cites}."


def get_provider(name: str):
    if name == "mock":
        return MockProvider()
    if name == "mock-refuse":
        return MockProvider(refuse=True)
    return get_llm_provider(name)


# ---------------------------------------------------------------------- helpers
def get_session():
    try:
        from database.connection import SessionLocal  # type: ignore

        return SessionLocal()
    except Exception:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        url = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/gst_sahayak")
        return sessionmaker(bind=create_engine(url))()


def recall(expected, found):
    expected, found = set(expected), set(found)
    return round(len(expected & found) / len(expected), 4) if expected else None


def precision(expected, found):
    expected, found = set(expected), set(found)
    return round(len(expected & found) / len(found), 4) if (expected and found) else None


def key_fact_rate(key_facts, answer):
    if not key_facts:
        return None
    low = (answer or "").lower()
    hits = 0
    for fact in key_facts:
        options = [fact] if isinstance(fact, str) else list(fact)
        if any(o.lower() in low for o in options):
            hits += 1
    return round(hits / len(key_facts), 4)


def unsupported_numbers(answer, context_text, query):
    """Numbers in the answer (source tags and list numbering removed) that appear neither in the sources
    (as digits or written as words) nor in the question."""
    known = {n.replace(",", "") for n in NUMBER.findall(context_text)} | {
        n.replace(",", "") for n in NUMBER.findall(query)}
    known |= number_words_to_digits(context_text) | number_words_to_digits(query)
    body = re.sub(r"(?m)^\s*(?:[-*]\s*)?\d+[.)]\s+", "", strip_tags(answer or ""))
    found = {n.replace(",", "").rstrip(".") for n in NUMBER.findall(body)}
    return sorted(n for n in found if n and n not in known)


_UNITS = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen "
    "seventeen eighteen nineteen".split())}
_TENS = {w: 10 * (i + 2) for i, w in enumerate("twenty thirty forty fifty sixty seventy eighty ninety".split())}
_SCALES = {"thousand": 1000, "lakh": 100000, "crore": 10000000}


def number_words_to_digits(text):
    """'one hundred and eighty' -> '180', 'twenty lakh' -> '20' and '2000000'. Lets the number check recognise
    figures the Acts write in words."""
    tokens = re.findall(r"[a-z]+", (text or "").lower())
    known = set(_UNITS) | set(_TENS) | set(_SCALES) | {"hundred"}
    out, i = set(), 0
    while i < len(tokens):
        if tokens[i] not in known:
            i += 1
            continue
        total = current = 0
        j = i
        while j < len(tokens):
            t = tokens[j]
            if t in _UNITS:
                current += _UNITS[t]
            elif t in _TENS:
                current += _TENS[t]
            elif t == "hundred":
                current = (current or 1) * 100
            elif t in _SCALES:
                out.add(str(current or 1))
                total += (current or 1) * _SCALES[t]
                current = 0
            elif t == "and" and j + 1 < len(tokens) and tokens[j + 1] in known:
                pass
            else:
                break
            j += 1
        out.add(str(total + current))
        i = max(j, i + 1)
    return out


def mean(values):
    values = [v for v in values if v is not None]
    return round(sum(values) / len(values), 4) if values else None


def p50(values):
    values = [v for v in values if v is not None]
    return round(statistics.median(values), 2) if values else None


def pct(x):
    return "-" if x is None else f"{x * 100:.0f}%"


def num(x, nd=2):
    return "-" if x is None else f"{x:.{nd}f}"


# ------------------------------------------------------------------- main logic
def run_query(db, q, providers, top_k):
    chunks, trace = retrieval_service.search_hybrid_chunks_with_trace(db, q["query"], top_k=top_k)
    status, best = rag_service.evaluate_evidence_quality(chunks)
    retrieved_keys = [section_key(c) for c in chunks]
    expected = q.get("expected_sections", [])
    base = {
        "query_id": q["id"],
        "type": q.get("type"),
        "query": q["query"],
        "expect_refusal": q.get("expect_refusal", False),
        "evidence_status": status,
        "best_score": best,
        "retrieval_mode": trace["retrieval_mode"],
        "queries_used": trace["queries_used"],
        "retrieved_sections": retrieved_keys,
        "retrieved_labels": [c.get("citation_label") for c in chunks],
        "retrieved_chunk_ids": [c.get("chunk_id") for c in chunks],
        "retrieval_recall": recall(expected, retrieved_keys),
        "chunk_recall": recall(q.get("expected_chunks", []), [c.get("chunk_id") for c in chunks]),
    }
    rows = []
    if not providers:  # retrieval-only
        return base, rows

    if status == "insufficient":
        for p in providers:
            rows.append({**base, "provider": p, "model": "-", "llm_called": False, "system_refused": True,
                         "success": True, "error": None, "latency_s": 0.0, "retries": 0, "answer": REFUSAL_MESSAGE,
                         "refused": True, "citations": [], "invalid_citations": [], "uncited_answer": False,
                         "cited_sections": [], "cited_recall": None, "cited_precision": None,
                         "unsupported_numbers": [], "key_fact_hit": None})
        return base, rows

    prompt, sources = rag_service.build_grounded_prompt(chunks, q["query"], status)
    context_text = "\n".join(s["text"] + " " + s["label"] for s in sources)

    def transient(err):
        return any(m in (err or "") for m in ("503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED", "timed out"))

    def call(name):
        model, retries, err = name, 0, None
        for attempt in range(3):  # retry temporary provider overloads (503/429) twice
            start = time.time()
            try:
                provider = get_provider(name)
                model = getattr(provider, "_model_name", name)
                if not provider.is_configured():
                    return name, model, False, "not configured", 0.0, None, retries
                answer = provider.generate_response(prompt)
                return name, model, True, None, round(time.time() - start, 2), answer, retries
            except Exception as exc:
                err = str(exc).replace("\n", " ")[:300]
                if attempt < 2 and transient(err):
                    retries += 1
                    time.sleep(5 * (attempt + 1) ** 2)
                    continue
                return name, model, False, err, round(time.time() - start, 2), None, retries
        return name, model, False, err, 0.0, None, retries

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(providers))) as pool:
        outcomes = list(pool.map(call, providers))

    for name, model, ok, err, latency, answer, retries in outcomes:
        cit = extract_citations(answer, sources) if ok else {
            "citations": [], "invalid_citations": [], "uncited_answer": False, "refused": False,
            "cited_sections": [],
        }
        rows.append({
            **base,
            "provider": name, "model": model, "llm_called": True, "system_refused": False,
            "success": ok, "error": err, "latency_s": latency, "retries": retries, "answer": answer or "",
            "refused": cit["refused"],
            "citations": [c["tag"] for c in cit["citations"]],
            "invalid_citations": cit["invalid_citations"],
            "uncited_answer": cit["uncited_answer"],
            "cited_sections": cit["cited_sections"],
            "cited_recall": recall(expected, cit["cited_sections"]) if ok else None,
            "cited_precision": precision(expected, cit["cited_sections"]) if ok else None,
            "unsupported_numbers": unsupported_numbers(answer, context_text, q["query"]) if ok else [],
            "key_fact_hit": key_fact_rate(q.get("key_facts", []), answer) if ok else None,
        })
    return base, rows


def aggregate(rows):
    out = {}
    for provider in sorted({r["provider"] for r in rows}):
        pr = [r for r in rows if r["provider"] == provider and r["llm_called"]]
        ok = [r for r in pr if r["success"]]
        answered = [r for r in ok if not r["refused"] and not r["expect_refusal"]]
        expect_ref = [r for r in ok if r["expect_refusal"]]
        out[provider] = {
            "model": next((r["model"] for r in pr), "-"),
            "llm_calls": len(pr),
            "success_rate": round(len(ok) / len(pr), 4) if pr else None,
            "latency_avg_s": mean([r["latency_s"] for r in ok]),
            "latency_p50_s": p50([r["latency_s"] for r in ok]),
            "valid_citation_rate": round(
                sum(1 for r in answered if r["citations"] and not r["invalid_citations"]) / len(answered), 4
            ) if answered else None,
            "invalid_citations_per_answer": round(
                sum(len(r["invalid_citations"]) for r in answered) / len(answered), 3) if answered else None,
            "cited_section_recall": mean([r["cited_recall"] for r in answered]),
            "cited_section_precision": mean([r["cited_precision"] for r in answered]),
            "key_fact_hit": mean([r["key_fact_hit"] for r in answered]),
            "unsupported_numbers_per_answer": round(
                sum(len(r["unsupported_numbers"]) for r in answered) / len(answered), 3) if answered else None,
            "wrongly_refused_answerable": sum(1 for r in ok if r["refused"] and not r["expect_refusal"]),
            "answered_when_should_refuse": sum(1 for r in expect_ref if not r["refused"]),
        }
    return out


def best_per_metric(agg):
    rules = [
        ("Fastest (avg latency)", "latency_avg_s", min),
        ("Highest valid-citation rate", "valid_citation_rate", max),
        ("Highest cited-section recall", "cited_section_recall", max),
        ("Highest key-fact hit", "key_fact_hit", max),
        ("Fewest unsupported numbers", "unsupported_numbers_per_answer", min),
        ("Highest success rate", "success_rate", max),
    ]
    lines = []
    for label, key, fn in rules:
        vals = {p: a[key] for p, a in agg.items() if a.get(key) is not None}
        if vals:
            best = fn(vals.values())
            winners = [p for p, v in vals.items() if v == best]
            lines.append(f"- {label}: {', '.join(winners)} ({best})")
    return lines


def write_summary(path, per_query, rows, agg, top_k, providers):
    lines = [f"# GST Sahayak evaluation ({datetime.now().strftime('%Y-%m-%d %H:%M')})", ""]
    lines.append(f"Retrieved top_k={top_k} chunks once per question; every provider got the same prompt. "
                 f"Providers: {', '.join(providers) if providers else '(retrieval only)'}.")
    lines.append("")
    lines += ["## Retrieval", "",
              "| Question | Type | Best score | Evidence | Section recall | Chunk recall | Retrieved sections |",
              "|---|---|---|---|---|---|---|"]
    for b in per_query:
        lines.append(f"| {b['query_id']} | {b['type']} | {b['best_score']} | {b['evidence_status']} | "
                     f"{pct(b['retrieval_recall'])} | {pct(b['chunk_recall'])} | "
                     f"{', '.join(dict.fromkeys(b['retrieved_sections']))} |")
    sec = [b["retrieval_recall"] for b in per_query if b["retrieval_recall"] is not None]
    chk = [b["chunk_recall"] for b in per_query if b["chunk_recall"] is not None]
    lines.append("")
    lines.append(f"Average section recall: {pct(mean(sec))} over {len(sec)} questions. Average chunk recall "
                 f"(the exact sub-section needed): {pct(mean(chk))} over {len(chk)} questions that list expected_chunks.")
    ans_scores = [b["best_score"] for b in per_query if b["type"] == "answerable"]
    oos_scores = [b["best_score"] for b in per_query if b["type"] == "out_of_scope"]
    lines.append("")
    if ans_scores and oos_scores:
        lo, hi = min(ans_scores), max(oos_scores)
        lines.append(f"Threshold calibration: lowest answerable best_score = {lo}, highest out-of-scope = {hi}.")
        if hi < lo:
            lines.append(f"They separate. A WEAK_EVIDENCE_THRESHOLD around {round((lo + hi) / 2, 2)} would refuse "
                         "every out-of-scope question and answer every answerable one (set it in backend/.env).")
        else:
            lines.append("They OVERLAP, so no single threshold separates them; improve retrieval or rely on the "
                         "model's own refusal.")
    sys_ref = [b for b in per_query if b["expect_refusal"]]
    if sys_ref:
        ok = sum(1 for b in sys_ref if b["evidence_status"] == "insufficient")
        lines.append(f"Refusal by the retrieval guard (no LLM call): {ok}/{len(sys_ref)} of the questions that "
                     "should be refused.")
    if agg:
        lines += ["", "## Models (answerable questions only unless stated)", "",
                  "| Provider | Model | Success | Avg s | p50 s | Valid citations | Invalid cites/ans | "
                  "Cited-section recall | Cited-section precision | Key-fact hit | Unsupported nums/ans | "
                  "Wrongly refused | Answered when should refuse |",
                  "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for p, a in agg.items():
            lines.append(f"| {p} | {a['model']} | {pct(a['success_rate'])} | {num(a['latency_avg_s'])} | "
                         f"{num(a['latency_p50_s'])} | {pct(a['valid_citation_rate'])} | "
                         f"{num(a['invalid_citations_per_answer'], 2)} | {pct(a['cited_section_recall'])} | "
                         f"{pct(a['cited_section_precision'])} | {pct(a['key_fact_hit'])} | "
                         f"{num(a['unsupported_numbers_per_answer'], 2)} | {a['wrongly_refused_answerable']} | "
                         f"{a['answered_when_should_refuse']} |")
        lines += ["", "## Best model per metric", ""] + best_per_metric(agg)
        lines += ["", "No automatic per-query model routing is implemented; this table is the basis on which a routing "
                      "policy could be designed.", "",
                  "Notes: 'Unsupported numbers' and 'invalid citations' are hallucination PROXIES. Factual "
                  "correctness still needs the manual_correctness column in results.csv (0 = wrong, 1 = partly, 2 = correct)."]
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--providers", default=DEFAULT_PROVIDERS)
    ap.add_argument("--top-k", type=int, default=None, help="default: the service default (DEFAULT_TOP_K)")
    ap.add_argument("--queries", default=str(Path(__file__).with_name("queries.json")))
    ap.add_argument("--only", default="", help="comma-separated query ids")
    ap.add_argument("--out-dir", default="")
    ap.add_argument("--retrieval-only", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="use the fake 'mock' model, no API calls")
    args = ap.parse_args()

    args.top_k = args.top_k or retrieval_service.default_top_k
    queries = json.loads(Path(args.queries).read_text(encoding="utf-8"))
    if args.only:
        wanted = {x.strip() for x in args.only.split(",")}
        queries = [q for q in queries if q["id"] in wanted]
    providers = [] if args.retrieval_only else (["mock"] if args.dry_run else
                                                 [p.strip().lower() for p in args.providers.split(",") if p.strip()])

    out_dir = Path(args.out_dir) if args.out_dir else Path(__file__).parent / "results" / datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir.mkdir(parents=True, exist_ok=True)

    db = get_session()
    per_query, all_rows = [], []
    try:
        for i, q in enumerate(queries, start=1):
            base, rows = run_query(db, q, providers, args.top_k)
            per_query.append(base)
            all_rows.extend(rows)
            print(f"[{i}/{len(queries)}] {q['id']}: best={base['best_score']} {base['evidence_status']} "
                  f"recall={base['retrieval_recall']} sections={list(dict.fromkeys(base['retrieved_sections']))}")
            for r in rows:
                state = "refused(system)" if r["system_refused"] else ("ERROR " + str(r["error"])[:60] if not r["success"]
                                                                       else f"{r['latency_s']}s cites={r['citations']}")
                print(f"      {r['provider']:<10} {state}")
    finally:
        db.close()

    agg = aggregate(all_rows) if providers else {}
    (out_dir / "results.json").write_text(
        json.dumps({"per_query": per_query, "rows": all_rows, "aggregate": agg}, indent=2, ensure_ascii=False),
        encoding="utf-8")
    if all_rows:
        cols = ["query_id", "type", "provider", "model", "llm_called", "system_refused", "success", "error",
                "latency_s", "retries", "evidence_status", "best_score", "retrieval_recall", "chunk_recall", "cited_sections", "cited_recall",
                "cited_precision", "citations", "invalid_citations", "uncited_answer", "unsupported_numbers",
                "key_fact_hit", "refused", "expect_refusal", "manual_correctness", "answer"]
        with open(out_dir / "results.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            for r in all_rows:
                row = dict(r)
                for k in ("cited_sections", "citations", "invalid_citations", "unsupported_numbers"):
                    row[k] = ";".join(row.get(k) or [])
                row["manual_correctness"] = ""
                w.writerow(row)
    write_summary(out_dir / "summary.md", per_query, all_rows, agg, args.top_k, providers)
    print(f"\nWrote {out_dir / 'summary.md'}")


if __name__ == "__main__":
    main()