from pathlib import Path

from cka.infrastructure.processing.loader import DocumentLoader, LoadedPage


class PlainTextLoader(DocumentLoader):
    def supports(self, filename: str) -> bool:
        return filename.lower().endswith(".txt")

    def load(self, path: Path) -> list[LoadedPage]:
        text = path.read_text(encoding="utf-8")
        return [LoadedPage(text=text, page_number=None)]
