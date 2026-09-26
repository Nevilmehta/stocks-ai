"""Finds which seeded companies are mentioned in a piece of free text (a
research chat message, for example). Shared by the research router (to route
a chat message to the right stock context) and the admin analytics endpoint
(to tally "most researched stocks" from message history).
"""

from __future__ import annotations

import re
import uuid

from app.models.company import Company

CORPORATE_SUFFIXES = {"ltd", "limited", "inc", "corp", "corporation", "company", "co"}


def _company_name_words(name: str) -> set[str]:
    return {
        stripped
        for w in name.lower().split()
        if len(stripped := w.strip(".,&")) >= 4 and stripped not in CORPORATE_SUFFIXES
    }


def distinctive_words_by_company(companies: list[Company]) -> dict[uuid.UUID, set[str]]:
    """Words from each company's name, excluding any word shared by more than
    one seeded company (e.g. "Tata" is ambiguous between Tata Motors and Tata
    Consultancy Services, so neither may be matched on "Tata" alone)."""
    company_words = {c.id: _company_name_words(c.name) for c in companies}
    word_owners: dict[str, set[uuid.UUID]] = {}
    for company_id, words in company_words.items():
        for word in words:
            word_owners.setdefault(word, set()).add(company_id)

    return {
        company_id: {w for w in words if len(word_owners[w]) == 1}
        for company_id, words in company_words.items()
    }


def find_mentioned_companies(text: str, companies: list[Company], limit: int = 3) -> list[Company]:
    distinctive = distinctive_words_by_company(companies)
    matched: list[Company] = []
    for company in companies:
        if re.search(rf"\b{re.escape(company.symbol)}\b", text, re.IGNORECASE):
            matched.append(company)
            continue
        words = distinctive.get(company.id, set())
        if any(re.search(rf"\b{re.escape(word)}\b", text, re.IGNORECASE) for word in words):
            matched.append(company)
    return matched[:limit]
