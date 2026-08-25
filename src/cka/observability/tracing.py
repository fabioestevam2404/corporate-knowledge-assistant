from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Tracer

SERVICE = "corporate-knowledge-assistant"


def configure_tracing(otlp_endpoint: str, enabled: bool) -> Tracer:
    """Configures a real OpenTelemetry TracerProvider exporting to an OTLP
    collector (Jaeger in this project — see docker-compose.yml). When
    `enabled` is False (e.g. some test contexts), spans are still created
    (no code branches on tracing) but never exported anywhere.
    """
    provider = TracerProvider(resource=Resource.create({SERVICE_NAME: SERVICE}))
    if enabled:
        exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return trace.get_tracer(SERVICE)


def get_tracer() -> Tracer:
    return trace.get_tracer(SERVICE)


def current_trace_id() -> str:
    span = trace.get_current_span()
    context = span.get_span_context()
    if context.trace_id == 0:
        return ""
    return format(context.trace_id, "032x")
