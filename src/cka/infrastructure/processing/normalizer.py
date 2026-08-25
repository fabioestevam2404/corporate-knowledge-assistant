import re

_MULTIPLE_BLANK_LINES = re.compile(r"\n{3,}")
_TRAILING_WHITESPACE = re.compile(r"[ \t]+\n")
_MULTIPLE_SPACES = re.compile(r"[ \t]{2,}")


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _TRAILING_WHITESPACE.sub("\n", text)
    text = _MULTIPLE_SPACES.sub(" ", text)
    text = _MULTIPLE_BLANK_LINES.sub("\n\n", text)
    return text.strip()
