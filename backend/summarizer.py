def summarize_text(text: str, max_sentences: int = 5) -> str:
    """Extracts key sentences to form a concise legal executive summary."""
    if not text or not text.strip():
        return "No content available to summarize."

    # Clean and split into sentences
    cleaned_text = " ".join(text.split())
    sentences = [
        s.strip()
        for s in cleaned_text.replace("?", ".").replace("!", ".").split(".")
        if len(s.strip()) > 15
    ]

    if not sentences:
        return text[:300] + "..." if len(text) > 300 else text

    # Return top key sentences as summary
    selected = sentences[:max_sentences]
    return ". ".join(selected) + "."