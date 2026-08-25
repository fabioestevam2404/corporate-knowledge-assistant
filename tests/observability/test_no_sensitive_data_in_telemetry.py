"""Extends the "no raw content logged" discipline (established informally
since Block 1/2) with an explicit, automated check: a distinctive marker
placed in the query text must never leak into structured logs or Prometheus
metric labels — both are low-cardinality/operational surfaces, not content
stores.
"""

from collections.abc import Callable

from _pytest.capture import CaptureFixture
from fastapi.testclient import TestClient

from cka.main import app

SENSITIVE_MARKER = "SUPER_SECRET_QUERY_MARKER_XYZ123"


def test_query_text_never_appears_in_structured_logs(
    capsys: CaptureFixture[str], auth_headers: Callable[[str], dict[str, str]]
) -> None:
    with TestClient(app) as client:
        client.post(
            "/ask",
            json={"query": f"What is {SENSITIVE_MARKER}?"},
            headers=auth_headers("employee"),
        )

    captured = capsys.readouterr()
    assert SENSITIVE_MARKER not in captured.out
    assert SENSITIVE_MARKER not in captured.err


def test_query_text_never_appears_in_metrics_output(
    auth_headers: Callable[[str], dict[str, str]],
) -> None:
    with TestClient(app) as client:
        client.post(
            "/ask",
            json={"query": f"What is {SENSITIVE_MARKER}?"},
            headers=auth_headers("employee"),
        )
        response = client.get("/metrics")

    assert SENSITIVE_MARKER not in response.text
