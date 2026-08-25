# ADR-011 — Observability and LLMOps

`Status: Accepted` · `Data: 2026-08-25` · `Projeto: Corporate Knowledge Assistant`

## 1. Contexto

Até o fim do Bloco 2, `trace_id` no `/ask` era um reaproveitamento do `request_id` gerado pelo
middleware do Bloco 1 — documentado como placeholder deliberado até este bloco. Sem tracing
distribuído real, investigar uma requisição lenta ou com erro significava ler logs
estruturados em sequência, sem visualização de onde o tempo foi gasto entre autenticação,
retrieval, reranking e geração.

## 2. Decisão

OpenTelemetry real (SDK + `FastAPIInstrumentor` para spans HTTP automáticos, spans manuais
para `hybrid_retrieval`, `reranking`, `context_building`, `llm_generation`,
`citation_validation`), exportado via OTLP para Jaeger. `trace_id` no `/ask` passa a ser o
trace id real do OpenTelemetry (`observability/tracing.py::current_trace_id`), não mais o
`request_id`. Métricas Prometheus reais (`http_requests_total`,
`http_request_duration_seconds`, `rag_retrieval_duration_seconds`,
`rag_reranking_duration_seconds`, `llm_requests_total`) expostas em `GET /metrics`, raspadas
por Prometheus, visualizadas em um dashboard Grafana provisionado via arquivo (não configurado
manualmente pela UI — reprodutível).

## 3. Justificativa

Logs, métricas e traces respondem perguntas diferentes: logs dizem "o que aconteceu", métricas
dizem "com que frequência/magnitude", traces dizem "onde exatamente, e qual foi o caminho da
requisição" — os três já eram um objetivo desde o Fase 1 §2, mas só agora tracing e métricas
se tornam reais (logging estruturado já era real desde o Bloco 1).

## 4. Alternativas consideradas

- **`prompt_injection_detected_total` como métrica real**: rejeitado por enquanto — sem um
  sinal de detecção real (ADR-009 rejeita bloqueio por palavra-chave), adicionar essa métrica
  seria expor uma superfície de observabilidade sempre zerada, uma falsa aparência de
  monitoramento. Documentado como gap conhecido, não implementado silenciosamente.
- **Instrumentação automática de SQLAlchemy**: adiada — o valor incremental sobre os spans
  manuais já existentes (que já cobrem o tempo de retrieval, que é onde o SQL relevante roda)
  é menor do que o custo de mais uma dependência neste bloco.
- **Configurar dashboards manualmente na UI do Grafana**: rejeitado — não é reproduzível;
  provisionamento via arquivo (`docker/grafana/provisioning/`) garante que o dashboard exista
  de verdade a cada `docker compose up`, não apenas na máquina de quem o configurou.

## 5. Consequências

### ✅ Positivas
- `trace_id` retornado por `/ask` agora é real e consultável na API do Jaeger.
- `/metrics` real, raspado por Prometheus real, visualizado em dashboard real.

### ⚠️ Negativas
- Tracing real (`OTEL_TRACES_ENABLED=true`) exige Jaeger rodando — desabilitado por padrão em
  `.env` local (`uv run` direto), habilitado no `docker-compose.yml`. Documentado, não uma
  armadilha silenciosa (ver comentário em `.env`/`.env.example`).

## 6. Considerações de segurança

Nenhum conteúdo de documento, prompt completo ou texto de query aparece em atributos de span,
labels de métrica ou logs — apenas identificadores, contagens e durações (testado
explicitamente em `tests/observability/test_no_sensitive_data_in_telemetry.py`, que verifica
um marcador sensível de teste real nunca aparecer nem em logs nem em `/metrics`).

## 7. Critérios de revisão

Revisar se um sinal real de detecção de prompt injection for implementado (então
`prompt_injection_detected_total` passa a fazer sentido), ou se o volume de tráfego justificar
sampling de traces em vez de exportar 100%.

## 8. Status

Accepted.
