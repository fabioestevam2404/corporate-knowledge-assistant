from pathlib import Path

from cka.infrastructure.processing.pdf_loader import PdfDocumentLoader
from cka.infrastructure.processing.text_loader import PlainTextLoader

SAMPLES_DIR = Path(__file__).resolve().parents[2] / "data" / "raw" / "samples"


def test_plain_text_loader_supports_txt_only() -> None:
    loader = PlainTextLoader()

    assert loader.supports("policy.txt") is True
    assert loader.supports("policy.pdf") is False


def test_plain_text_loader_loads_real_sample_as_single_page() -> None:
    loader = PlainTextLoader()

    pages = loader.load(SAMPLES_DIR / "remote-work-policy.txt")

    assert len(pages) == 1
    assert pages[0].page_number is None
    assert "Remote Work Policy" in pages[0].text


def test_pdf_loader_supports_pdf_only() -> None:
    loader = PdfDocumentLoader()

    assert loader.supports("policy.pdf") is True
    assert loader.supports("policy.txt") is False


def test_pdf_loader_loads_real_sample_pdf_with_page_numbers() -> None:
    loader = PdfDocumentLoader()

    pages = loader.load(SAMPLES_DIR / "expense-reimbursement-policy.pdf")

    assert len(pages) == 2
    assert pages[0].page_number == 1
    assert pages[1].page_number == 2
    assert "Expense Reimbursement Policy" in pages[0].text
    assert "Submission Deadline" in pages[1].text
