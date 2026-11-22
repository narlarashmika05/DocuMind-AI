"""Language detection for English and Telugu.

Telugu has its own script (Unicode block U+0C00-U+0C7F), so counting characters in
that block is more reliable on short questions than a statistical language-ID model.
"""

TELUGU_START, TELUGU_END = 0x0C00, 0x0C7F

LANGUAGE_NAMES = {"en": "English", "te": "Telugu"}


def telugu_ratio(text: str) -> float:
    letters = [ch for ch in text if ch.isalpha()]
    if not letters:
        return 0.0
    return sum(TELUGU_START <= ord(ch) <= TELUGU_END for ch in letters) / len(letters)


def detect_language(text: str) -> str:
    """'te' if at least 30% of letters are Telugu (mixed "Telugu + English terms" counts as Telugu)."""
    return "te" if telugu_ratio(text) >= 0.3 else "en"


def resolve_answer_language(requested: str, question_language: str) -> str:
    """requested is 'auto' (answer in the question's language), 'en' or 'te'."""
    return question_language if requested == "auto" else requested
