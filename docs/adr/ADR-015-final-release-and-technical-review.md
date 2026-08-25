# ADR-015 — Final Release e Technical Review

`Status: Accepted` · `Data: 2026-08-25` · `Projeto: Corporate Knowledge Assistant`

## 1. Contexto

Este é o ADR que fecha o exercício que deu origem a todo o Bloco 4: a
instrução original pedia para executar os critérios de Definition of Done
contra o código real do repositório, revisar arquivo por arquivo, rodar os
testes e preencher o Release Gate v1.0.0 com evidências reais — em vez de
marcar entregas como prontas apenas conceitualmente. Este sprint (15) é
onde essa promessa é cumprida por completo: suíte final, baseline de
performance real, manifesto de release, checklists finais e o documento
consolidado `RELEASE_GATE_v1.0.0.md`.

## 2. Decisão

- Re-execução completa e real da suíte (lint, format, mypy, pytest
  unit+integration+security+observability, `scripts/evaluate.py`) —
  **não** reaproveitada de execuções anteriores.
- **Baseline de performance real**: script próprio (`perf_baseline.py`,
  scratchpad — não commitado, os números resultantes é que são a
  evidência real) fazendo 25 chamadas reais a `/retrieve` e 25 a `/ask`
  contra a stack ao vivo, calculando p50/p95/p99 reais.
- `docs/release-gate/ai-release-manifest.json`: valores reais (versão,
  commit, modelos, resultado da avaliação, baseline de performance,
  resultado da suíte, scans de segurança, gaps conhecidos) — nenhum
  placeholder.
- `docs/release-gate/RELEASE_GATE_v1.0.0.md`: documento final,
  consolidando todos os 8 gates do roadmap contra evidência real já
  reunida nos Blocos 1–4, sem duplicar `PROGRESS.md` — referenciando-o.
- Tags reais `v1.0.0-rc.1` depois `v1.0.0`, criadas localmente (sem
  remote, sem push) uma vez que a suíte estivesse verde de verdade.

## 3. Justificativa

Um "Release Gate" que não é preenchido depois de rodar os comandos reais
contra o estado real do repositório é exatamente o problema que esta
instrução original pediu para corrigir. Cada número neste sprint —
incluindo os que não são bonitos (ver defeito abaixo) — vem de um comando
real executado nesta sessão, não de um valor estimado ou copiado de um
bloco anterior sem re-verificação.

## 4. Um defeito real e significativo encontrado durante este próprio sprint

A re-execução da suíte completa, exigida por este sprint, foi o que
revelou que **`tests/conftest.py`'s `db_session` fixture apagava os dados
reais de desenvolvimento** (documentos e usuários reais, incluindo dados
seedados em blocos anteriores) porque testes locais apontavam para o mesmo
banco usado para demo/validação manual. Corrigido na raiz (banco de teste
dedicado `cka_test`, nunca mais o banco real) — ver
`docs/release-gate/PROGRESS.md`, seção Sprint 15, para o incidente
completo, incluindo uma anomalia observada (mas não forense/confirmada)
durante a recuperação, declarada honestamente como tal em vez de omitida.
Este é exatamente o tipo de achado que valida a tese central deste
exercício: só rodar os comandos de verdade, contra o estado real, revela
esse tipo de problema — nenhuma leitura do roadmap ou do código
isoladamente o teria capturado.

## 5. Consequências

### ✅ Positivas
- Todo número no `RELEASE_GATE_v1.0.0.md` final é rastreável a um comando
  real executado e documentado.
- O defeito de isolamento de testes deste sprint — que poderia ter
  destruído dados de demo de qualquer desenvolvedor rodando a suíte
  localmente, indefinidamente, sem nunca ser notado — está corrigido antes
  do release, não depois.

### ⚠️ Negativas
- O outlier real de latência em `/retrieve` (p99 = 5850ms contra uma
  baseline de 175–334ms) não foi suavizado nem re-executado até
  desaparecer — reportado como está, com a leitura honesta de que uma
  única amostra lenta não é, por si só, evidência de um problema
  sistemático, mas também não deve ser descartada sem investigação futura.

## 6. Considerações de segurança

Nenhuma credencial real aparece no manifesto ou no Release Gate final —
apenas hash de commit, nomes de modelo, e métricas agregadas.

## 7. Critérios de revisão

Revisar o outlier de latência do `/retrieve` se ele se repetir em execuções
futuras do baseline. Revisar `ai-release-manifest.json` a cada release
subsequente — ele deve ser regenerado, nunca copiado do release anterior.

## 8. Status

Accepted.
