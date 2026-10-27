"""Pure-function tests (no database, no network, no API keys).

Run from the backend folder:  python -m pytest tests -q
"""
from services.citations import (
    REFUSAL_MESSAGE,
    build_sources,
    extract_citations,
    find_tags,
    is_refusal,
    section_key,
    split_label,
    strip_tags,
)
from services.query_expansion import QueryExpansionService
from services.retrieval_service import (
    RetrievalService,
    _boost_for,
    extract_section_mentions,
    parse_chunk_label,
)
from services.rag_service import RAGService
from services.multi_model_verification_service import MultiModelVerificationService


def chunk(cid, label, body="body text", act="CGST Act 2017", section="22", sub="(1)", score=0.5):
    return {
        "chunk_id": cid, "text": f"[{label}]\n{body}", "act": act, "section": section, "sub": sub,
        "citation_label": f"{act}, Section {section}{sub or ''}", "source_url": "http://x", "similarity_score": score,
        "hybrid_score": score,
    }


# ------------------------------------------------------------------ label parsing
def test_parse_label_simple():
    r = parse_chunk_label("[CGST Act 2017, Section 22(1) - Persons liable for registration]\n(1) text")
    assert r["act"] == "CGST Act 2017" and r["section"] == "22" and r["sub"] == "(1)"
    assert r["title"] == "Persons liable for registration"
    assert r["citation_label"] == "CGST Act 2017, Section 22(1)"


def test_parse_label_part_range_and_explanation():
    assert parse_chunk_label("[CGST Act 2017, Section 22(1), part 1/2 - T]\nx")["sub"] == "(1)"
    assert parse_chunk_label("[CGST Act 2017, Section 25(2)-(3) - T]\nx")["sub"] == "(2)-(3)"
    r = parse_chunk_label("[CGST Act 2017, Section 16(2) Explanation, part 1/3 - T]\nx")
    assert r["section"] == "16" and r["sub"] == "(2)"
    r = parse_chunk_label("[CGST Act 2017, Section 24, part 2/2 - Compulsory registration in certain cases]\nx")
    assert r["section"] == "24" and r["sub"] is None
    assert parse_chunk_label("[IGST Act 2017, Section 7(1)-(1A) - Inter-State supply]\nx")["sub"] == "(1)-(1A)"


def test_parse_label_missing():
    assert parse_chunk_label("no label here")["section"] is None
    assert parse_chunk_label("")["act"] is None


# ----------------------------------------------------------------- section mentions
def test_section_mentions_explicit_only():
    assert extract_section_mentions("Section 16 conditions for claiming input tax credit")["mentions"] == [("16", None)]
    assert extract_section_mentions("what does sec 22(1) say")["mentions"] == [("22", "1")]
    assert extract_section_mentions("see s. 24")["mentions"] == [("24", None)]
    assert extract_section_mentions("sections 16 and section 17")["mentions"] == [("16", None), ("17", None)]


def test_bare_numbers_are_not_sections():
    q = "I earn 15 lakh/year, half from Indian clients and half from a US client"
    assert extract_section_mentions(q)["mentions"] == []
    assert extract_section_mentions("it has 16 pages")["mentions"] == []


def test_bare_section_2_ignored_but_2_6_ok():
    assert extract_section_mentions("CGST Section 2")["mentions"] == []
    assert extract_section_mentions("CGST Section 2(6)")["mentions"] == [("2", "6")]


def test_act_detection():
    assert extract_section_mentions("CGST Section 16")["act"] == "CGST Act 2017"
    assert extract_section_mentions("IGST Section 16")["act"] == "IGST Act 2017"
    assert extract_section_mentions("CGST and IGST section 16")["act"] is None


def test_boost_matching():
    m = extract_section_mentions("IGST Section 16")
    assert _boost_for({"act": "IGST Act 2017", "section": "16", "sub": "(1)"}, m, 0.25) == 0.25
    assert _boost_for({"act": "CGST Act 2017", "section": "16", "sub": "(1)"}, m, 0.25) == 0.0
    m2 = extract_section_mentions("section 25(3)")
    assert _boost_for({"act": "CGST Act 2017", "section": "25", "sub": "(2)-(3)"}, m2, 0.25) == 0.25
    assert _boost_for({"act": "CGST Act 2017", "section": "25", "sub": "(4)-(5)"}, m2, 0.25) == 0.0
    assert _boost_for({"act": "CGST Act 2017", "section": "22", "sub": "(1)"}, m2, 0.25) == 0.0


# ----------------------------------------------------------------------- diversity
def test_diversify_caps_but_exempts_explicit_and_fills():
    rs = [dict(chunk(f"c{i}", "x", section="2", act="CGST Act 2017", score=1 - i * 0.01), hybrid_score=1 - i * 0.01)
          for i in range(6)]
    rs.append(dict(chunk("o1", "x", section="22", score=0.5), hybrid_score=0.5))
    out = RetrievalService._diversify(rs, 4, {"act": None, "mentions": []})
    secs = [r["section"] for r in out]
    assert secs.count("2") == 3 and "22" in secs  # cap 3, other section pulled in
    out_explicit = RetrievalService._diversify(rs, 5, {"act": None, "mentions": [("2", "1")]})
    assert len(out_explicit) == 5


# ------------------------------------------------------------------ query expansion
def test_expansion_flagship_covers_key_sections():
    q = ("I'm a freelance graphic designer in Delhi, earning 15 lakh/year, half from Indian clients and half from "
         "a US client. Do I need GST registration, and what applies to each income source?")
    qs = QueryExpansionService().expand_query_deterministic(q)
    assert qs[0] == q
    joined = " | ".join(qs)
    assert "CGST Section 22" in joined and "CGST Section 24" in joined
    assert "IGST Section 16" in joined and "IGST Section 13" in joined


def test_expansion_word_boundaries():
    svc = QueryExpansionService()
    assert svc.expand_query_deterministic("how do I switch my solution provider") == [
        "how do I switch my solution provider"
    ]
    assert len(svc.expand_query_deterministic("can I claim ITC on my laptop")) > 1


def test_expansion_never_emits_bare_section_2():
    from services.query_expansion import RULES
    import re
    for _, subs in RULES:
        for s in subs:
            assert not re.search(r"\bSection 2\b(?!\()", s), s


def test_expansion_unrelated_query_untouched():
    assert QueryExpansionService().expand_query_deterministic("What is the weather in Delhi today?") == [
        "What is the weather in Delhi today?"
    ]


# --------------------------------------------------------------------- citations
def test_split_label_and_sources():
    c = chunk("a1", "CGST Act 2017, Section 22(1) - Persons liable", body="(1) Every supplier...")
    label, body = split_label(c)
    assert label == "CGST Act 2017, Section 22(1) - Persons liable" and body.startswith("(1) Every")
    srcs = build_sources([c, chunk("a2", "CGST Act 2017, Section 24 - Compulsory", section="24", sub=None)])
    assert [s["tag"] for s in srcs] == ["S1", "S2"]
    assert section_key(srcs[1]) == "CGST 24"


def test_find_tags_formats():
    assert find_tags("a [S1] b [S2][S3] c [S4, S5]") == ["S1", "S2", "S3", "S4", "S5"]
    assert find_tags("see [Section 22] and [1]") == []
    assert strip_tags("Registered if turnover exceeds 20 lakh [S1].") == "Registered if turnover exceeds 20 lakh ."


def test_extract_citations_valid_invalid_uncited():
    srcs = build_sources([chunk("a1", "CGST Act 2017, Section 22(1) - T"),
                          chunk("a2", "IGST Act 2017, Section 16(1) - T", act="IGST Act 2017", section="16")])
    r = extract_citations("Register above the limit [S1]. Exports are zero rated [S2][S9].", srcs)
    assert [c["tag"] for c in r["citations"]] == ["S1", "S2"]
    assert r["invalid_citations"] == ["S9"] and r["uncited_answer"] is False
    assert r["cited_sections"] == ["CGST 22", "IGST 16"]
    assert extract_citations("No tags at all.", srcs)["uncited_answer"] is True
    refusal = extract_citations(REFUSAL_MESSAGE, srcs)
    assert refusal["refused"] is True and refusal["uncited_answer"] is False
    assert is_refusal("Sorry. I could not find sufficient supporting evidence in the available GST documents.")


# ------------------------------------------------------------------ rag + compare
def test_evidence_thresholds():
    svc = RAGService(strong_threshold=0.65, weak_threshold=0.40)
    assert svc.evaluate_evidence_quality([])[0] == "insufficient"
    assert svc.evaluate_evidence_quality([{"similarity_score": 0.39}])[0] == "insufficient"
    assert svc.evaluate_evidence_quality([{"similarity_score": 0.40}])[0] == "weak"
    assert svc.evaluate_evidence_quality([{"similarity_score": 0.65}])[0] == "strong"


def test_prompt_contains_tags_rules_and_no_page_or_score():
    svc = RAGService()
    prompt, sources = svc.build_grounded_prompt(
        [chunk("a1", "CGST Act 2017, Section 22(1) - T", body="(1) Every supplier shall be liable")],
        "Do I need to register?", "strong")
    assert "[S1] CGST Act 2017, Section 22(1) - T" in prompt
    assert "Every supplier shall be liable" in prompt
    assert REFUSAL_MESSAGE in prompt
    assert "Relevance Score" not in prompt and "Page:" not in prompt and "VECTOR_ONLY" not in prompt.upper()
    assert "partly cover" in svc.build_grounded_prompt([chunk("a1", "x")], "q", "weak")[0]
    assert sources[0]["tag"] == "S1"


def test_legal_reference_regex_keeps_subsections():
    svc = MultiModelVerificationService()
    refs = svc.extract_legal_references("Under Section 16(2) and Section 22 (1) read with Rule 96A.")
    assert "Section 16(2)" in refs and "Section 22" in refs and "Rule 96A" in refs


def test_compare_answers_uses_citations():
    svc = MultiModelVerificationService()
    base = {"success": True}
    same = [
        {**base, "provider": "a", "answer": "Register above twenty lakh rupees turnover [S1].", "cited_sections": ["CGST 22"]},
        {**base, "provider": "b", "answer": "Register above twenty lakh rupees turnover [S1].", "cited_sections": ["CGST 22"]},
    ]
    assert svc.compare_answers(same)["overall_status"] == "agreement"
    diff = [
        {**base, "provider": "a", "answer": "alpha beta gamma delta", "cited_sections": ["CGST 22"]},
        {**base, "provider": "b", "answer": "completely different words here", "cited_sections": ["IGST 16"]},
    ]
    assert svc.compare_answers(diff)["overall_status"] == "disagreement"
    one = [same[0], {"success": False, "provider": "b", "answer": None}]
    assert svc.compare_answers(one)["overall_status"] == "insufficient_models"


# ------------------------------------------------------- merge: honest similarity
def test_similarity_score_is_original_query_score_and_cap_default():
    from services import retrieval_service as rs

    def res(cid, section, score):
        return {"chunk_id": cid, "act": "CGST Act 2017", "section": section, "sub": "(1)", "hybrid_score": score,
                "similarity_score": score, "retrieval_mode": "python-fallback"}

    calls = []

    def fake_candidates(self, db, q, k, threshold, fy, asof, vw, kw_w, boost):
        calls.append(q)
        if len(calls) == 1:  # original question
            return [res("a", "22", 0.44), res("b", "24", 0.30)]
        return [res("a", "22", 0.60), res("c", "16", 0.97)]  # sub-query: chunk c only found here

    svc = rs.RetrievalService()
    orig = rs.RetrievalService._candidates
    rs.RetrievalService._candidates = fake_candidates
    try:
        out, trace = svc.search_hybrid_chunks_with_trace(
            None, "do I need gst registration", top_k=5, enable_query_expansion=True)
    finally:
        rs.RetrievalService._candidates = orig
    by = {r["chunk_id"]: r for r in out}
    assert by["a"]["hybrid_score"] == 0.60 and by["a"]["similarity_score"] == 0.44
    assert by["c"]["hybrid_score"] == 0.97 and by["c"]["similarity_score"] == 0.0  # found only via sub-query
    assert out[0]["chunk_id"] == "c"  # ranking still uses the boosted score
    assert RAGService().evaluate_evidence_quality(out)[1] == 0.44  # evidence guard ignores sub-query inflation
    assert rs.MAX_PER_SECTION == 3


def test_returns_rule_needs_gst_context():
    svc = QueryExpansionService()
    q13 = "Which returns must a registered freelancer file for GST?"
    joined = " | ".join(svc.expand_query_deterministic(q13))
    assert "CGST Section 39" in joined and "CGST Section 37" in joined
    # an income-tax question must NOT be pulled towards GST returns
    q16 = "How do I file my income tax return and claim 80C deductions?"
    assert svc.expand_query_deterministic(q16) == [q16]


def _run_eval_module():
    import importlib.util
    from pathlib import Path
    path = Path(__file__).resolve().parent.parent / "eval" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_eval_number_check_understands_words_and_list_numbers():
    ev = _run_eval_module()
    assert {"180"} <= ev.number_words_to_digits("within a period of one hundred and eighty days")
    assert {"20", "2000000"} <= ev.number_words_to_digits("exceeds twenty lakh rupees")
    ctx = "within one hundred and eighty days; exceeds twenty lakh rupees. Section 16(2)"
    ans = "1. First point [S1]\n2. Second point\nPay within 180 days; limit is 20 lakh and 99 other. Section 16(2)"
    assert ev.unsupported_numbers(ans, ctx, "my question") == ["99"]