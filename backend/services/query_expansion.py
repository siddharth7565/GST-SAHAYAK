"""Query expansion for GST Sahayak.

Freelancers ask in everyday words ("do I need GST registration", "my US client"); the Acts use
statutory wording ("liable to be registered", "export of services"). A small sentence embedding
model cannot bridge that gap reliably, so each question is expanded into a few short
statutory-style sub-queries that are searched in addition to the original.

Rules are deterministic (regex with word boundaries). Sub-queries only point at sections that
exist in the corpus (CGST 2, 7, 9, 13, 15, 16, 17, 18, 22, 23, 24, 25, 31, 37, 39 and
IGST 2, 5, 7, 8, 12, 13, 16). Section hints always name the Act ("CGST Section 22") so that the
retrieval section-boost lands on the right Act. Never use a bare "Section 2": it would boost
every definition.

Optional: QUERY_REWRITE_LLM=true also asks the default LLM for extra sub-queries (silent
fallback to the rules on any failure).
"""
import json
import os
import re
from typing import List, Tuple

MAX_SUBQUERIES = int(os.getenv("MAX_SUBQUERIES", "6"))

_FOREIGN_PLACES = (
    r"us|usa|u\.s\.|u\.s\.a\.|uk|u\.k\.|europe|european|eu|america|american|canada|canadian|australia|"
    r"australian|singapore|dubai|uae|germany|german|france|french|japan|japanese|foreign|overseas|"
    r"international|abroad"
)

# (compiled pattern, [sub-queries in priority order])
RULES: List[Tuple[re.Pattern, List[str]]] = [
    (
        re.compile(
            r"\b(regist\w*|gstin|gst number|gst no|threshold|turnover|exemption limit|need gst|require gst)\b",
            re.I,
        ),
        [
            "every supplier liable to be registered if aggregate turnover exceeds twenty lakh rupees CGST Section 22",
            "persons required to be registered compulsory registration inter-State taxable supply CGST Section 24",
            "aggregate turnover means aggregate value of all taxable supplies exempt supplies exports CGST Section 2(6)",
        ],
    ),
    (
        re.compile(r"\bvoluntar\w*", re.I),
        ["person not liable to be registered may get himself registered voluntarily CGST Section 25(3)"],
    ),
    (
        re.compile(r"\b(not liable|exempt from regist\w*|no need to regist\w*|agricultur\w*)\b", re.I),
        ["persons not liable for registration CGST Section 23"],
    ),
    (
        re.compile(
            r"\bexport\w*|\boutside india\b|\bnon-?resident\b|\bnri\b|\bforeign\b|\boverseas\b|\babroad\b|"
            r"\binternational\b|\bamerican\b|"
            rf"\b(?:{_FOREIGN_PLACES})\s+(?:based\s+)?(?:client|clients|customer|customers|company|companies|"
            rf"firm|agency|startup|buyer)\b|"
            rf"\b(?:client|clients|customer|customers)\s+(?:in|from|based in)\s+(?:the\s+)?(?:{_FOREIGN_PLACES})\b",
            re.I,
        ),
        [
            "export of services zero rated supply IGST Section 16",
            "place of supply of services where location of recipient is outside India IGST Section 13",
            "export of services means supply of any service supplier located in India recipient outside India "
            "payment received in convertible foreign exchange IGST Section 2(6)",
        ],
    ),
    (
        re.compile(r"\b(lut|letter of undertaking|bond|zero[- ]?rated|refund)\b", re.I),
        [
            "zero rated supply export of services refund of integrated tax IGST Section 16",
            "supply without payment of integrated tax under bond or letter of undertaking IGST Section 16(3)",
        ],
    ),
    (
        re.compile(
            r"\b(indian|domestic|local)\s+(?:client|clients|customer|customers)\b|\bwithin india\b|"
            r"\bintra-?\s?state\b|\bsame state\b",
            re.I,
        ),
        [
            "place of supply of services where location of supplier and recipient is in India IGST Section 12",
            "intra-State supply location of supplier and place of supply in same State IGST Section 8",
            "levy of central tax and State tax on intra-State supplies CGST Section 9",
        ],
    ),
    (
        re.compile(
            r"\binter-?\s?state\b|\bother states?\b|\banother state\b|\bdifferent states?\b|\boutside (?:my|the|our) state\b",
            re.I,
        ),
        [
            "inter-State supply location of supplier and place of supply in different States IGST Section 7",
            "persons making inter-State taxable supply compulsory registration CGST Section 24",
            "levy of integrated tax on inter-State supplies IGST Section 5",
        ],
    ),
    (
        re.compile(r"\bplace of supply\b|\bwhich state\b|\bwhere (?:do|should|must|to) i (?:pay|charge)\b", re.I),
        ["place of supply of services IGST Section 12", "place of supply of services outside India IGST Section 13"],
    ),
    (
        re.compile(
            r"\b(itc|input tax credit|input credit|tax credit|claim(?:ing)? (?:the )?(?:gst|credit)|"
            r"business expenses?|laptop|equipment|software subscription)\b",
            re.I,
        ),
        [
            "registered person entitled to take credit of input tax conditions tax invoice receipt of services "
            "CGST Section 16",
            "input tax credit not available blocked credits personal consumption CGST Section 17",
        ],
    ),
    (
        re.compile(r"\breverse charge\b|\brcm\b|\bimport of services?\b", re.I),
        [
            "liability to pay tax on reverse charge basis CGST Section 9(3)",
            "import of services reverse charge integrated tax IGST Section 5",
        ],
    ),
    (
        re.compile(r"\btax invoice\b|\binvoic\w*|\bbilling\b|\bbill\b", re.I),
        ["tax invoice issued by registered person supplying taxable services CGST Section 31"],
    ),
    (
        re.compile(
            r"\bgst returns?\b|\bgstr[- ]?\w*|\bfile (?:a |my |the |your )?returns?\b|\bfiling\b|\bfurnish\w*|"
            r"\breturns?\b(?=.*\bgst\b)|\bgst\b(?=.*\breturns?\b)",
            re.I,
        ),
        [
            "furnishing details of outward supplies CGST Section 37",
            "furnishing of returns CGST Section 39",
        ],
    ),
    (
        re.compile(r"\btime of supply\b|\badvance (?:payment|received)\b|\bwhen (?:do|does|should|must|is) .{0,40}\b(?:pay|liable)\b", re.I),
        ["time of supply of services liability to pay tax arises CGST Section 13"],
    ),
    (
        re.compile(r"\b(value of (?:the )?supply|transaction value|discount|valuation|taxable value)\b", re.I),
        ["value of taxable supply transaction value CGST Section 15"],
    ),
    (
        re.compile(r"\b(gst rate|rate of gst|how much (?:gst|tax)|gst on|liable to pay|tax liability|levy)\b", re.I),
        [
            "levy and collection of central goods and services tax on supply CGST Section 9",
            "scope of supply CGST Section 7",
        ],
    ),
]


class QueryExpansionService:
    def __init__(self):
        self.use_llm = os.getenv("QUERY_REWRITE_LLM", "false").lower() == "true"

    def expand_query_deterministic(self, query: str) -> List[str]:
        """Original query first, then up to MAX_SUBQUERIES statutory-style sub-queries."""
        subs: List[str] = []
        for pattern, expansions in RULES:
            if pattern.search(query):
                for e in expansions:
                    if e not in subs:
                        subs.append(e)
        return [query] + subs[:MAX_SUBQUERIES]

    def _llm_subqueries(self, query: str) -> List[str]:
        try:
            from services.llm_providers import get_llm_provider

            provider = get_llm_provider("gemini")
            if not provider.is_configured():
                return []
            prompt = (
                "Rewrite this question from an Indian freelancer as 3 short search queries in the wording of "
                "the GST Acts. The knowledge base only has CGST Act 2017 sections 2, 7, 9, 13, 15, 16, 17, 18, "
                "22, 23, 24, 25, 31, 37, 39 and IGST Act 2017 sections 2, 5, 7, 8, 12, 13, 16. "
                'Return ONLY a JSON array of strings, e.g. ["...", "...", "..."].\n\n'
                f"Question: {query}"
            )
            raw = provider.generate_response(prompt)
            m = re.search(r"\[.*?\]", raw, re.DOTALL)
            if not m:
                return []
            items = json.loads(m.group(0))
            return [q.strip() for q in items if isinstance(q, str) and q.strip()][:3]
        except Exception:
            return []

    def expand_query(self, query: str) -> List[str]:
        queries = self.expand_query_deterministic(query)
        if self.use_llm:
            for q in self._llm_subqueries(query):
                if q not in queries:
                    queries.append(q)
        return queries


query_expansion_service = QueryExpansionService()