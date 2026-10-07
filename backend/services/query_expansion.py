"""
Query Expansion Service for GST Sahayak.

Maps freelancer natural-language phrasing to statutory legal terminology
to improve retrieval accuracy. Includes deterministic domain table and
optional LLM-based expansion.
"""
import os
import re
import json
from typing import List, Dict, Optional
from services.llm_providers import get_llm_provider

# Deterministic domain table: freelancer phrasing -> statutory terms
QUERY_EXPANSION_TABLE = {
    # Registration threshold
    "need GST registration": [
        "persons liable for registration",
        "aggregate turnover threshold",
        "compulsory registration"
    ],
    "do I need to register": [
        "persons liable for registration",
        "registration threshold",
        "aggregate turnover"
    ],
    "registration required": [
        "persons liable for registration",
        "compulsory registration"
    ],
    "40 lakh threshold": [
        "aggregate turnover threshold",
        "registration threshold",
        "aggregate turnover"
    ],

    # Foreign/export clients
    "US client": [
        "export of services",
        "zero-rated supply",
        "place of supply of services",
        "outside India"
    ],
    "foreign client": [
        "export of services",
        "zero-rated supply",
        "place of supply of services",
        "outside India"
    ],
    "abroad": [
        "export of services",
        "zero-rated supply",
        "place of supply",
        "outside India"
    ],
    "international client": [
        "export of services",
        "zero-rated supply",
        "place of supply of services"
    ],

    # LUT
    "LUT": [
        "letter of undertaking",
        "zero rated supply",
        "export of services"
    ],
    "letter of undertaking": [
        "letter of undertaking",
        "zero rated supply",
        "export of services"
    ],

    # ITC
    "ITC": [
        "input tax credit",
        "eligibility conditions",
        "Section 16"
    ],
    "input tax credit": [
        "input tax credit",
        "eligibility conditions",
        "Section 16"
    ],
    "claim credit": [
        "input tax credit",
        "eligibility conditions",
        "conditions for taking input tax credit"
    ],

    # Reverse charge
    "reverse charge": [
        "reverse charge mechanism",
        "Section 9(3)",
        "Section 9(4)"
    ],

    # Composition scheme
    "composition": [
        "composition scheme",
        "Section 10",
        "composition levy"
    ],

    # Inter-state
    "inter-state": [
        "inter-State supply",
        "compulsory registration",
        "Section 24"
    ],
    "interstate": [
        "inter-State supply",
        "compulsory registration",
        "Section 24"
    ],

    # Place of supply
    "where to pay": [
        "place of supply",
        "place of supply of goods",
        "place of supply of services"
    ],
    "which state": [
        "place of supply",
        "place of supply of goods",
        "place of supply of services"
    ],

    # Invoicing
    "invoice": [
        "tax invoice",
        "invoice requirements",
        "Section 31"
    ],
    "bill": [
        "tax invoice",
        "invoice requirements"
    ],

    # Returns
    "file return": [
        "return filing",
        "GSTR-1",
        "GSTR-3B",
        "Section 39"
    ],
    "filing": [
        "return filing",
        "GSTR-1",
        "GSTR-3B"
    ],
}


class QueryExpansionService:
    """
    Service for expanding natural-language queries into statutory terminology
    to improve retrieval accuracy. Uses deterministic domain table by default,
    with optional LLM-based expansion.
    """

    def __init__(self):
        self.use_llm = os.getenv("QUERY_REWRITE_LLM", "false").lower() == "true"

    def expand_query_deterministic(self, query: str) -> List[str]:
        """
        Expand query using deterministic domain table.
        Returns list of sub-queries (original + expanded terms).
        """
        queries = [query]
        query_lower = query.lower()

        # Check for matches in expansion table
        for phrase, expansions in QUERY_EXPANSION_TABLE.items():
            if phrase.lower() in query_lower:
                # Add each expansion as a separate sub-query
                for expansion in expansions:
                    # Create sub-query by replacing the phrase with statutory terms
                    sub_query = query_lower.replace(phrase.lower(), expansion)
                    if sub_query not in [q.lower() for q in queries]:
                        queries.append(sub_query.capitalize())

        # Limit to 4 sub-queries total
        return queries[:4]

    def expand_query_llm(self, query: str) -> List[str]:
        """
        Expand query using LLM (fallback to deterministic on failure).
        Returns list of sub-queries as JSON.
        """
        if not self.use_llm:
            return self.expand_query_deterministic(query)

        try:
            provider = get_llm_provider("gemini")  # Use default provider
            if not provider.is_configured():
                return self.expand_query_deterministic(query)

            prompt = f"""You are a GST legal terminology expert. Convert this natural-language freelancer question into 3-4 statutory-style sub-queries that would match GST Act text better.

Original query: "{query}"

Return ONLY a JSON array of strings, like this:
["query 1", "query 2", "query 3"]

Do not include any explanation, just the JSON array."""

            response = provider.generate_response(prompt)

            # Parse JSON response
            # Extract JSON array from response (handle potential markdown code blocks)
            json_match = re.search(r'\[.*?\]', response, re.DOTALL)
            if json_match:
                queries = json.loads(json_match.group(0))
                if isinstance(queries, list) and all(isinstance(q, str) for q in queries):
                    # Ensure original query is included
                    if query not in queries:
                        queries.insert(0, query)
                    return queries[:4]

            # Fallback to deterministic if parsing fails
            return self.expand_query_deterministic(query)

        except Exception as e:
            # Silent fallback to deterministic on any error
            return self.expand_query_deterministic(query)

    def expand_query(self, query: str) -> List[str]:
        """
        Main entry point: expand query using configured method.
        Returns list of sub-queries including original.
        """
        if self.use_llm:
            return self.expand_query_llm(query)
        else:
            return self.expand_query_deterministic(query)


# Global singleton instance
query_expansion_service = QueryExpansionService()
