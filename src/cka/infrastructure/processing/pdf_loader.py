from pathlib import Path

from pypdf import PdfReader

from cka.infrastructure.processing.loader import DocumentLoader, LoadedPage


class PdfDocumentLoader(DocumentLoader):
    """Extracts text page-by-page so page numbers survive into citations."""

    def supports(self, filename: str) -> bool:
        return filename.lower().endswith(".pdf")

    def load(self, path: Path) -> list[LoadedPage]:
        reader = PdfReader(str(path))
        return [
            LoadedPage(text=page.extract_text(), page_number=index + 1)
            for index, page in enumerate(reader.pages)
        ]
