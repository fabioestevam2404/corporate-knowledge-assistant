# ADR-001 — Seleção e Governança das Fontes Documentais

`Status: Accepted` · `Data: 2026-08-24` · `Projeto: Corporate Knowledge Assistant`

## 1. Contexto

Um assistente de RAG corporativo só é confiável se as fontes que alimentam sua base de
conhecimento forem rastreáveis, licenciadas de forma clara e auditáveis. Sem um mecanismo
central de governança, é fácil que documentos entrem no índice sem proveniência conhecida,
sem controle de versão e sem validação de licença — o que compromete tanto a confiabilidade
das respostas quanto a defensabilidade legal do sistema.

## 2. Decisão

Adotar um **Source Registry** (`data/sources/registry.yaml`) como mecanismo central de
governança de fontes. Nenhum documento pode ser ingerido a menos que sua fonte esteja
registrada, com `status: approved` e `allowed_for_ingestion: true`. O MVP usa apenas
documentos com licença clara e proveniência conhecida — no Bloco 1, um pequeno conjunto de
documentos de exemplo autorados especificamente para este projeto (não dados corporativos
reais nem material confidencial de terceiros).

## 3. Justificativa

A confiabilidade de um sistema RAG depende tanto da qualidade do modelo quanto da governança
da fonte: proveniência, auditabilidade, versionamento e redução de risco de licenciamento. Um
registro central permite responder, para qualquer trecho retornado pelo sistema, "de onde
veio isso, sob qual licença, e quando foi aprovado".

## 4. Alternativas consideradas

- **Upload manual de documentos**: rejeitado — sem rastreabilidade de proveniência.
- **Documentos aleatórios da internet**: rejeitado — licença e veracidade não verificáveis.
- **Documentos corporativos reais**: rejeitado para o MVP — risco de confidencialidade e
  propriedade intelectual.
- **Documentos sintéticos gerados por IA**: adiado — não descartado para uso futuro em
  testes, mas não usado como base primária do MVP.

## 5. Consequências

### ✅ Positivas
- Rastreabilidade e auditabilidade completas de qualquer documento no índice.
- Redução de risco de licenciamento.
- Base sólida para os testes de autorização documental (ACL) do Bloco 3.

### ⚠️ Negativas
- Exige monitoramento contínuo de mudanças em fontes externas quando estas forem adicionadas.
- Overhead de processo: nenhum documento entra "rápido" sem passar pelo registro.

## 6. Considerações de segurança

O Source Registry é também um controle de segurança: ele é o único portão de entrada para o
pipeline de ingestão (ver `ValidateSource` em `src/cka/application/validate_source.py`).
Classificações de sensibilidade (`access_level`) registradas aqui alimentam diretamente o
controle de acesso documental implementado em blocos futuros.

## 7. Critérios de revisão

Revisar esta decisão se o volume de fontes externas crescer a ponto de exigir uma ferramenta
de governança dedicada (fora de um arquivo YAML), ou ao integrar as fontes públicas externas
referenciadas no roadmap original (documentos governamentais brasileiros).

## 8. Status

Accepted.
