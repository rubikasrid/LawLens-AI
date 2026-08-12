import re

RISK_PATTERNS = [
    {
        "category": "Indemnification & Liability",
        "keywords": [r"indemnif", r"hold harmless", r"unlimited liability", r"consequential damages"],
        "level": "High",
        "advice": "Review indemnification caps. Ensure liability is limited to total contract value."
    },
    {
        "category": "Termination Rights",
        "keywords": [r"terminate for convenience", r"without cause", r"notice period", r"immediate termination"],
        "level": "Medium",
        "advice": "Check notice period (prefer 30+ days) and compensation for unbilled work in progress."
    },
    {
        "category": "Intellectual Property",
        "keywords": [r"intellectual property", r"work for hire", r"exclusive owner", r"patent", r"copyright"],
        "level": "Low",
        "advice": "Verify that pre-existing proprietary assets and tools remain excluded from full assignment."
    },
    {
        "category": "Confidentiality & Non-Disclosure",
        "keywords": [r"confidential", r"non-disclosure", r"trade secret", r"proprietary information"],
        "level": "Low",
        "advice": "Ensure mutual confidentiality obligations and clear exclusion criteria."
    }
]

def extract_risk_clauses(text: str):
    """Analyzes text for key risk clauses and categories."""
    sentences = re.split(r'(?<=[.!?]) +', text)
    flagged_clauses = []

    for sentence in sentences:
        sentence_clean = sentence.strip()
        if len(sentence_clean) < 20:
            continue

        for pattern in RISK_PATTERNS:
            for kw in pattern["keywords"]:
                if re.search(kw, sentence_clean, re.IGNORECASE):
                    flagged_clauses.append({
                        "category": pattern["category"],
                        "risk_level": pattern["level"],
                        "clause_text": sentence_clean,
                        "recommendation": pattern["advice"]
                    })
                    break

    # Limit to top 6 highlighted clauses to keep summary concise
    return flagged_clauses[:6]