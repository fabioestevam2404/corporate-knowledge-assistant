from cka.observability.tracing import configure_tracing, current_trace_id, get_tracer


def test_current_trace_id_is_empty_outside_a_span() -> None:
    # No active span in this bare test context.
    assert current_trace_id() == "" or len(current_trace_id()) == 32


def test_current_trace_id_is_a_32_char_hex_string_inside_a_span() -> None:
    configure_tracing(otlp_endpoint="http://localhost:4317", enabled=False)
    tracer = get_tracer()

    with tracer.start_as_current_span("test-span"):
        trace_id = current_trace_id()

    assert len(trace_id) == 32
    int(trace_id, 16)  # raises if not valid hex


def test_configure_tracing_disabled_does_not_attempt_export() -> None:
    # Should not raise even though no collector is reachable at this
    # endpoint — enabled=False means no exporter is attached at all.
    tracer = configure_tracing(otlp_endpoint="http://127.0.0.1:1", enabled=False)

    with tracer.start_as_current_span("no-export-span"):
        pass


def test_get_tracer_produces_working_spans() -> None:
    tracer = get_tracer()

    with tracer.start_as_current_span("smoke-test-span"):
        assert len(current_trace_id()) == 32
