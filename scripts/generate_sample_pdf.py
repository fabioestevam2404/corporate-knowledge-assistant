"""Generates the real 2-page sample PDF fixture used to exercise PdfDocumentLoader.

Run once with: uv run python scripts/generate_sample_pdf.py
Regenerate only if the sample content needs to change.
"""

from pathlib import Path

from fpdf import FPDF

SAMPLES_DIR = Path(__file__).resolve().parents[1] / "data" / "raw" / "samples"
OUTPUT_PATH = SAMPLES_DIR / "expense-reimbursement-policy.pdf"

PAGE_1_TITLE = "Expense Reimbursement Policy (Sample)"
PAGE_1_BODY = (
    "Classification: internal\n"
    "License: CC0-1.0 (authored as sample/placeholder content for this project)\n"
    "Version: 1.0\n\n"
    "1. Purpose\n"
    "This sample policy is placeholder content used to exercise the PDF ingestion "
    "pipeline, including page-aware chunking and citation page numbers. It is not a "
    "real corporate policy.\n\n"
    "2. Eligible Expenses\n"
    "Employees may submit reimbursement requests for pre-approved travel, client "
    "meals, and required work equipment, provided original receipts are attached."
)

PAGE_2_TITLE = "Expense Reimbursement Policy (Sample) - continued"
PAGE_2_BODY = (
    "3. Submission Deadline\n"
    "Reimbursement requests must be submitted within thirty days of the expense "
    "date. Requests submitted after this window require manager approval.\n\n"
    "4. Approval Workflow\n"
    "Requests under a fixed threshold are auto-approved after manager sign-off; "
    "requests above the threshold additionally require finance review."
)


def _add_page(pdf: FPDF, title: str, body: str) -> None:
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.multi_cell(w=pdf.epw, h=10, text=title)
    pdf.ln(4)
    pdf.set_font("Helvetica", "", 11)
    for paragraph in body.split("\n\n"):
        pdf.multi_cell(w=pdf.epw, h=7, text=paragraph)
        pdf.ln(4)


def build_pdf() -> FPDF:
    pdf = FPDF()
    _add_page(pdf, PAGE_1_TITLE, PAGE_1_BODY)
    _add_page(pdf, PAGE_2_TITLE, PAGE_2_BODY)
    return pdf


if __name__ == "__main__":
    build_pdf().output(str(OUTPUT_PATH))
    print(f"Wrote {OUTPUT_PATH}")
