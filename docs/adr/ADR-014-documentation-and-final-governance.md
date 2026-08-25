# ADR-014 — Documentação e Governança Final

`Status: Accepted` · `Data: 2026-08-25` · `Projeto: Corporate Knowledge Assistant`

## 1. Contexto

Até o fim do Sprint 13, a documentação do projeto existia espalhada e
incompleta: ADRs cobrindo decisões pontuais, `PROGRESS.md` como log
cumulativo de evidências, e nenhum conjunto coeso de arquitetura, API,
segurança consolidada, avaliação, operações ou governança de fontes. O
roadmap (Sprint 14 original) pede exatamente esse conjunto — este ADR
registra como ele foi produzido e por quê.

## 2. Decisão

Todo documento deste sprint foi escrito a partir do código e dos artefatos
reais do repositório, não copiado ou parafraseado do roadmap:

- `docs/architecture/{architecture,system-context,container-diagram,data-flow}.md`
  — extraídos de `src/cka/` diretamente (estrutura de diretórios real,
  spans reais do Jaeger do Bloco 3, endpoints reais).
- `docs/api/api.md` — todo endpoint e schema copiado dos modelos Pydantic
  reais em `api/routes/*.py`, não reescrito de memória.
- `docs/security/security.md` — complementa (não duplica)
  `threat-model.md` do Bloco 3, como referência prática de controles
  implementados, cada um citando seu arquivo/teste real.
- `docs/evaluation/{evaluation,results}.md` — `results.md` usa o
  `reports/evaluation_latest.json` real do Bloco 3, com uma seção explícita
  de "como ler esses números honestamente" (o gap real de nunca ter rodado
  contra um LLM real é declarado, não escondido atrás de números
  aparentemente bons).
- `docs/operations/{runbook,troubleshooting,disaster-recovery}.md` —
  `troubleshooting.md` e `disaster-recovery.md` documentam os incidentes
  reais deste próprio bloco (o defeito de `PermissionError`, o zumbi de PID
  1 que exigiu reiniciar o Windows) como conhecimento operacional genuíno,
  não cenários hipotéticos.
- `docs/governance/source-registry.md` — tabela gerada de
  `data/sources/registry.yaml` real (5 fontes, `SRC-SAMPLE-001..005`).
- `CHANGELOG.md` — gerado a partir do `git log` real deste repositório.

## 3. Justificativa

Documentação que diverge do código real é pior do que nenhuma documentação
— cria falsa confiança. Cada arquivo deste sprint foi escrito depois de ler
o código/artefato correspondente, não antes, e referencia arquivos/testes
específicos em vez de descrições genéricas, para que qualquer divergência
futura seja fácil de detectar (o caminho citado deixa de existir ou muda de
comportamento, evidenciando que a doc precisa de atualização).

## 4. Alternativas consideradas

- **Copiar a documentação diretamente do documento de roadmap original**:
  rejeitado — é exatamente o padrão que esta série de blocos existe para
  corrigir (marcar como "pronto" conceitualmente em vez de validar contra o
  código real).
- **Gerar `docs/api/api.md` automaticamente via OpenAPI/Swagger do
  FastAPI**: considerado, mas o schema OpenAPI automático do FastAPI já
  está disponível em tempo real via `/docs`/`/openapi.json` quando a API
  está rodando — um documento estático adicional só agrega valor se
  explicar comportamento que o schema não captura (ex: o fallback do
  `FakeLLMProvider`, o significado de `grounded`/`confidence`), então
  `api.md` foi escrito como uma camada de explicação sobre o schema real,
  não uma cópia dele.

## 5. Consequências

### ✅ Positivas
- Todo documento é verificável contra um arquivo/comando real citado nele
  mesmo — reduz a chance de a documentação apodrecer silenciosamente.
- `troubleshooting.md`/`disaster-recovery.md` capturam conhecimento
  operacional real e não-óbvio (o incidente do zumbi de PID 1) que não
  existiria se escrito antes dos Sprints 12–13 acontecerem de verdade.

### ⚠️ Negativas
- Volume grande de documentos escritos em sequência neste sprint — risco
  de pequenas inconsistências entre eles (ex: um endpoint renomeado depois
  não propagado a todos os lugares que o citam). Mitigado parcialmente por
  cada um citar o arquivo de código-fonte real como referência primária,
  não se apresentar como a única fonte de verdade.

## 6. Considerações de segurança

Nenhum segredo real (senhas, chaves, tokens) aparece em nenhum documento
deste sprint — exemplos usam placeholders (`REPLACE_ME`) ou tokens JWT
truncados (`eyJ...`) já presentes em evidências anteriores dos Blocos 1–3.

## 7. Critérios de revisão

Revisar `docs/api/api.md` sempre que um endpoint real mudar de assinatura.
Revisar `docs/evaluation/results.md` assim que um `ANTHROPIC_API_KEY` real
for configurado em qualquer ambiente — os números mudam de forma material
e a seção "o que este projeto nunca exercitou" deste documento deixa de se
aplicar.

## 8. Status

Accepted.
