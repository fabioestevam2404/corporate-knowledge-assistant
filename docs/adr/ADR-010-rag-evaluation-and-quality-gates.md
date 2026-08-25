# ADR-010 — RAG Evaluation and Quality Gates

`Status: Accepted` · `Data: 2026-08-25` · `Projeto: Corporate Knowledge Assistant`

## 1. Contexto

Até aqui, a qualidade do RAG era verificada apenas por testes unitários/integração pontuais
(um caso feliz, um caso de abstenção). Faltava um processo sistemático — um Golden Dataset
real, métricas de retrieval e geração calculadas de verdade, e um gate que falhe alto quando
a qualidade regride.

## 2. Decisão

Um framework de avaliação leve (`src/cka/evaluation/`) com três datasets reais
(`data/evaluation/{retrieval,generation,adversarial}.yaml`), rodando contra o corpus real de
4 documentos (não os 40 casos do roadmap original, que pressupõem um corpus externo maior —
ver nota de escopo no `docs/release-gate/PROGRESS.md`, Bloco 3).

- **Retrieval**: Recall@5, Precision@5, MRR, NDCG@5 — sempre computados, sem depender de LLM.
- **Geração**: Citation Accuracy e Citation Completeness (determinísticos, a partir do que o
  `AskKnowledgeBase` já valida); Abstention Accuracy (bate `grounded` contra
  `expected_behavior`); Faithfulness e Answer Relevance via LLM-as-a-Judge
  (`AnthropicLLMJudge`) — só computados quando há uma chave real configurada, nunca simulados.
- **Adversarial**: prompt injection (taxa de resistência — o modelo não pode obedecer à
  instrução embutida), documento não autorizado (deve abster), pergunta fora de domínio (deve
  abster).
- **Gate** (`evaluation.gate.check_gate`): compara contra thresholds em `Settings`
  (`evaluation_min_*`), falha alto (lista de violações) — nunca falha silenciosamente.
- **CLI** (`scripts/evaluate.py`): roda tudo contra a infraestrutura real (DB real, embeddings
  reais, reranker real), escreve `reports/evaluation_latest.{json,md}`, retorna código de saída
  não-zero se o gate falhar.

## 3. Justificativa

Separar métricas que dependem de LLM das que não dependem é essencial para que o gate de CI
seja determinístico mesmo sem uma chave de API configurada — Recall@5 e Citation Accuracy
sempre podem ser verificados; Faithfulness/Answer Relevance exigem julgamento qualitativo.

## 4. Alternativas consideradas

- **Dataset de 40 casos do roadmap original**: rejeitado para este bloco — pressupõe o corpus
  externo maior (documentos governamentais brasileiros) que ainda não foi integrado.
- **LLM-as-judge como fonte de verdade única**: rejeitado — LLM-as-judge nunca substitui
  métricas determinísticas, é um sinal qualitativo complementar (ADR-010 original do roadmap).

## 5. Consequências

### ✅ Positivas
- Relatório real (`reports/evaluation_latest.json`) com números medidos, não estimados.
- Gate falha alto e é testável (`tests/unit/test_evaluation_gate.py`).

### ⚠️ Negativas
- Corpus pequeno (4 documentos) limita a significância estatística das métricas — aceitável
  para este estágio, revisar ao integrar um corpus maior.

## 6. Considerações de segurança

Os casos adversariais reutilizam o documento de teste de prompt injection
(`SRC-SAMPLE-005`) e o cenário de documento não autorizado do Bloco 3 — a avaliação de
qualidade e a de segurança compartilham a mesma base de evidência real.

## 7. Critérios de revisão

Revisar ao integrar o corpus externo maior referenciado no roadmap original, ou se os
thresholds em `Settings` precisarem de calibração após mais execuções reais.

## 8. Status

Accepted.
