import structlog

from cka.application.rag.citation_validator import validate_citations
from cka.application.rag.confidence import LOW, compute_confidence
from cka.application.rag.context_builder import ContextBuilder
from cka.application.rag.prompt_builder import SYSTEM_PROMPT, PromptBuilder
from cka.application.retrieve_knowledge import RetrieveKnowledge
from cka.domain.evidence import Evidence, GroundedAnswer, SourceReference
from cka.domain.llm_provider import LLMProvider
from cka.domain.retrieval import AccessScope
from cka.observability.metrics import LLM_REQUESTS_TOTAL
from cka.observability.tracing import get_tracer

logger = structlog.get_logger(__name__)
tracer = get_tracer()

ABSTENTION_TEXT = (
    "Não encontrei evidências suficientes na base de conhecimento para responder a essa pergunta."
)


class AskKnowledgeBase:
    """Orchestrates the full RAG flow (ADR-008): retrieve -> rerank (inside
    RetrieveKnowledge) -> build context -> build prompt -> generate ->
    validate citations -> compute confidence -> respond.

    Never calls the LLM when there's no qualifying evidence — abstains
    immediately instead (Evidence First / No Evidence No Answer).
    """

    def __init__(
        self,
        retrieve_knowledge: RetrieveKnowledge,
        context_builder: ContextBuilder,
        prompt_builder: PromptBuilder,
        llm_provider: LLMProvider,
        min_retrieval_score: float,
        score_threshold: float,
        high_min_evidence: int,
        top_k: int = 5,
    ) -> None:
        self._retrieve_knowledge = retrieve_knowledge
        self._context_builder = context_builder
        self._prompt_builder = prompt_builder
        self._llm_provider = llm_provider
        self._min_retrieval_score = min_retrieval_score
        self._score_threshold = score_threshold
        self._high_min_evidence = high_min_evidence
        self._top_k = top_k

    def __call__(self, query_text: str, access_scope: AccessScope, trace_id: str) -> GroundedAnswer:
        logger.info("query_received", trace_id=trace_id)

        results = self._retrieve_knowledge(query_text, access_scope, top_k=self._top_k)
        qualifying = [r for r in results if r.score >= self._min_retrieval_score]

        if not qualifying:
            logger.info("answer_returned", trace_id=trace_id, grounded=False, abstained=True)
            return GroundedAnswer(
                answer=ABSTENTION_TEXT, sources=[], confidence=LOW, grounded=False
            )

        evidences = [
            Evidence(
                chunk_id=r.chunk_id,
                document_id=r.document_id,
                source_id=r.source_id,
                content=r.content,
                page_number=r.page_number,
                score=r.score,
            )
            for r in qualifying
        ]

        with tracer.start_as_current_span("context_building") as span:
            context, included_evidences = self._context_builder.build(evidences)
            user_prompt = self._prompt_builder.build_user_prompt(context, query_text)
            span.set_attribute("context.evidence_count", len(included_evidences))

        with tracer.start_as_current_span("llm_generation") as span:
            provider_name = type(self._llm_provider).__name__
            span.set_attribute("llm.provider", provider_name)
            logger.info("llm_requested", trace_id=trace_id, evidence_count=len(included_evidences))
            LLM_REQUESTS_TOTAL.labels(provider=provider_name).inc()
            llm_response = self._llm_provider.generate(SYSTEM_PROMPT, user_prompt)

        with tracer.start_as_current_span("citation_validation") as span:
            valid_citations = validate_citations(llm_response.citations, included_evidences)
            confidence = compute_confidence(
                included_evidences,
                total_citations=len(llm_response.citations),
                valid_citations=len(valid_citations),
                score_threshold=self._score_threshold,
                high_min_evidence=self._high_min_evidence,
            )
            span.set_attribute("citation.valid_count", len(valid_citations))
            span.set_attribute("citation.total_count", len(llm_response.citations))

        cited_ids = set(valid_citations)
        sources = [
            SourceReference(
                source_id=evidence.source_id,
                document_id=evidence.document_id,
                page_number=evidence.page_number,
                chunk_id=evidence.chunk_id,
            )
            for evidence in included_evidences
            if evidence.chunk_id in cited_ids
        ]

        grounded = len(valid_citations) > 0
        logger.info("answer_returned", trace_id=trace_id, grounded=grounded, confidence=confidence)

        return GroundedAnswer(
            answer=llm_response.answer,
            sources=sources,
            confidence=confidence,
            grounded=grounded,
        )
