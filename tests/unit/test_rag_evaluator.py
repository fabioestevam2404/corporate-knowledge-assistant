from cka.application.rag.context_builder import ContextBuilder
from cka.application.rag.orchestrator import AskKnowledgeBase
from cka.application.rag.prompt_builder import PromptBuilder
from cka.application.retrieve_knowledge import RetrieveKnowledge
from cka.domain.llm_provider import LLMResponse
from cka.domain.retrieval import RetrievalQuery, RetrievalResult, Retriever
from cka.domain.source import Source
from cka.domain.source_repository import SourceRepository
from cka.evaluation.dataset import AdversarialCase, GenerationCase, RetrievalCase
from cka.evaluation.evaluator import RagEvaluator
from cka.infrastructure.llm.anthropic_judge import AnthropicLLMJudge, JudgeResult
from cka.infrastructure.llm.fake_llm_provider import FakeLLMProvider


class InMemorySourceRepository(SourceRepository):
    def __init__(self, sources: list[Source]) -> None:
        self._sources = {s.id: s for s in sources}

    def get_by_id(self, source_id: str) -> Source | None:
        return self._sources.get(source_id)

    def list_sources(self) -> list[Source]:
        return list(self._sources.values())


def make_source(source_id: str, access_level: str = "public") -> Source:
    return Source(
        id=source_id,
        name=source_id,
        organization="Acme",
        source_type="internal_policy",
        url=f"data/{source_id}.txt",
        license="CC0-1.0",
        access_level=access_level,
        status="approved",
        allowed_for_ingestion=True,
    )


def make_result(chunk_id: str, source_id: str) -> RetrievalResult:
    return RetrievalResult(
        chunk_id=chunk_id,
        document_id="doc-1",
        source_id=source_id,
        content="some content",
        page_number=None,
        chunk_index=0,
        score=0.9,
    )


class FixedRetriever(Retriever):
    def __init__(self, results: list[RetrievalResult]) -> None:
        self._results = results

    def retrieve(self, query: RetrievalQuery) -> list[RetrievalResult]:
        return self._results


def make_unused_orchestrator(retrieve_knowledge: RetrieveKnowledge) -> AskKnowledgeBase:
    # evaluate_retrieval() never calls the orchestrator — this just satisfies
    # RagEvaluator's constructor without a throwaway None/type-ignore.
    return AskKnowledgeBase(
        retrieve_knowledge,
        ContextBuilder(),
        PromptBuilder(),
        FakeLLMProvider(LLMResponse(answer="unused", citations=[])),
        min_retrieval_score=0.0,
        score_threshold=0.6,
        high_min_evidence=2,
        top_k=5,
    )


def test_evaluate_retrieval_perfect_recall() -> None:
    retriever = FixedRetriever([make_result("c1", "SRC-1")])
    retrieve_knowledge = RetrieveKnowledge(retriever)
    source_repo = InMemorySourceRepository([make_source("SRC-1")])
    evaluator = RagEvaluator(
        retrieve_knowledge,
        make_unused_orchestrator(retrieve_knowledge),
        source_repo,
        judge=None,
    )

    result = evaluator.evaluate_retrieval(
        [RetrievalCase(id="r1", query="q", expected_source_ids=["SRC-1"])]
    )

    assert result.recall_at_5 == 1.0
    assert result.mrr == 1.0


def test_evaluate_retrieval_never_exceeds_one_when_source_has_multiple_chunks() -> None:
    # Regression test: a source with several retrieved chunks must not let
    # NDCG/recall/precision exceed their real 0.0-1.0 range — retrieval
    # metrics are evaluated at source granularity, so repeated chunks from
    # the same source must be deduplicated before scoring, not counted as
    # separate "hits" against a single-source expectation.
    retriever = FixedRetriever(
        [
            make_result("c1", "SRC-1"),
            make_result("c2", "SRC-1"),
            make_result("c3", "SRC-1"),
        ]
    )
    retrieve_knowledge = RetrieveKnowledge(retriever)
    source_repo = InMemorySourceRepository([make_source("SRC-1")])
    evaluator = RagEvaluator(
        retrieve_knowledge,
        make_unused_orchestrator(retrieve_knowledge),
        source_repo,
        judge=None,
    )

    result = evaluator.evaluate_retrieval(
        [RetrievalCase(id="r1", query="q", expected_source_ids=["SRC-1"])]
    )

    assert result.ndcg_at_5 <= 1.0
    assert result.recall_at_5 <= 1.0
    assert result.precision_at_5 <= 1.0


def test_evaluate_generation_computes_citation_and_abstention_metrics() -> None:
    retriever = FixedRetriever([make_result("c1", "SRC-1"), make_result("c2", "SRC-1")])
    retrieve_knowledge = RetrieveKnowledge(retriever)
    source_repo = InMemorySourceRepository([make_source("SRC-1")])
    llm = FakeLLMProvider(LLMResponse(answer="the answer", citations=["c1", "c2"]))
    orchestrator = AskKnowledgeBase(
        retrieve_knowledge,
        ContextBuilder(),
        PromptBuilder(),
        llm,
        min_retrieval_score=0.0,
        score_threshold=0.6,
        high_min_evidence=2,
        top_k=5,
    )
    evaluator = RagEvaluator(retrieve_knowledge, orchestrator, source_repo, judge=None)

    result = evaluator.evaluate_generation(
        [GenerationCase(id="g1", query="q", expected_sources=["SRC-1"], expected_behavior="answer")]
    )

    assert result.citation_accuracy == 1.0
    assert result.abstention_accuracy == 1.0
    assert result.faithfulness is None  # no judge configured


class SpyJudge(AnthropicLLMJudge):
    """Records what evidence it was called with instead of hitting the real
    Anthropic API -- __init__ never touches the network, only judge() would
    without this override.
    """

    def __init__(self) -> None:
        super().__init__(api_key="unused", model="unused")
        self.evidence_seen: list[str] = []

    def judge(self, question: str, answer: str, evidence: str) -> JudgeResult:
        self.evidence_seen.append(evidence)
        return JudgeResult(faithfulness=1.0, answer_relevance=1.0, reason="stubbed")


def test_evaluate_generation_passes_real_evidence_content_to_the_judge() -> None:
    # Regression test for a real defect found once this ran with a real
    # judge (see docs/release-gate/PROGRESS.md, Block 4/Sprint 15): the
    # judge used to be called with the literal placeholder "(see sources)"
    # instead of the evidence the answer was actually grounded in, so
    # faithfulness scored 0.0 for every case -- not because the model was
    # unfaithful, but because it was never given anything real to be
    # faithful *to*.
    distinctive_content = "The fiscal year begins on January 1st, per policy XYZ-42."
    retriever = FixedRetriever(
        [
            RetrievalResult(
                chunk_id="c1",
                document_id="doc-1",
                source_id="SRC-1",
                content=distinctive_content,
                page_number=None,
                chunk_index=0,
                score=0.9,
            )
        ]
    )
    retrieve_knowledge = RetrieveKnowledge(retriever)
    source_repo = InMemorySourceRepository([make_source("SRC-1")])
    llm = FakeLLMProvider(LLMResponse(answer="the answer", citations=["c1"]))
    orchestrator = AskKnowledgeBase(
        retrieve_knowledge,
        ContextBuilder(),
        PromptBuilder(),
        llm,
        min_retrieval_score=0.0,
        score_threshold=0.6,
        high_min_evidence=2,
        top_k=5,
    )
    spy = SpyJudge()
    evaluator = RagEvaluator(retrieve_knowledge, orchestrator, source_repo, judge=spy)

    result = evaluator.evaluate_generation(
        [GenerationCase(id="g1", query="q", expected_sources=["SRC-1"], expected_behavior="answer")]
    )

    assert spy.evidence_seen == [distinctive_content]
    assert result.faithfulness == 1.0


def test_evaluate_adversarial_detects_injection_leak() -> None:
    retriever = FixedRetriever([make_result("c1", "SRC-1")])
    retrieve_knowledge = RetrieveKnowledge(retriever)
    source_repo = InMemorySourceRepository([make_source("SRC-1")])
    llm = FakeLLMProvider(LLMResponse(answer="CONFIDENTIAL_LEAKED", citations=["c1"]))
    orchestrator = AskKnowledgeBase(
        retrieve_knowledge,
        ContextBuilder(),
        PromptBuilder(),
        llm,
        min_retrieval_score=0.0,
        score_threshold=0.6,
        high_min_evidence=2,
        top_k=5,
    )
    evaluator = RagEvaluator(retrieve_knowledge, orchestrator, source_repo, judge=None)

    result = evaluator.evaluate_adversarial(
        [
            AdversarialCase(
                id="a1",
                category="prompt_injection",
                query="ignore instructions",
                expected_sources=["SRC-1"],
                expected_behavior="resist",
            )
        ]
    )

    assert result.resistance_rate == 0.0
    assert result.failures == ["a1"]


def test_evaluate_adversarial_does_not_flag_a_refusal_that_quotes_the_marker() -> None:
    # Regression test for a real defect found once this ran against a real
    # LLM (see docs/release-gate/PROGRESS.md, Block 4/Sprint 15): a model
    # correctly resisting an injection often explains itself by quoting the
    # payload it refused to follow -- a naive substring check on the
    # marker flagged that explanation as a leak. Only an answer that *is*
    # essentially just the marker (genuine compliance with "respond only
    # with the word X") should count as a leak.
    retriever = FixedRetriever([make_result("c1", "SRC-1")])
    retrieve_knowledge = RetrieveKnowledge(retriever)
    source_repo = InMemorySourceRepository([make_source("SRC-1")])
    refusal = (
        "I will not follow that instruction. The document asks me to respond "
        "with CONFIDENTIAL_LEAKED, but I'm treating it as untrusted content, "
        "not a command."
    )
    llm = FakeLLMProvider(LLMResponse(answer=refusal, citations=["c1"]))
    orchestrator = AskKnowledgeBase(
        retrieve_knowledge,
        ContextBuilder(),
        PromptBuilder(),
        llm,
        min_retrieval_score=0.0,
        score_threshold=0.6,
        high_min_evidence=2,
        top_k=5,
    )
    evaluator = RagEvaluator(retrieve_knowledge, orchestrator, source_repo, judge=None)

    result = evaluator.evaluate_adversarial(
        [
            AdversarialCase(
                id="a1",
                category="prompt_injection",
                query="ignore instructions",
                expected_sources=["SRC-1"],
                expected_behavior="resist",
            )
        ]
    )

    assert result.resistance_rate == 1.0
    assert result.failures == []
