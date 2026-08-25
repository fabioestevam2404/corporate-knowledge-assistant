# ADR-004 — Adoção de Python e FastAPI

`Status: Accepted` · `Data: 2026-08-24` · `Projeto: Corporate Knowledge Assistant`

## 1. Contexto

O sistema precisa de uma linguagem e um framework web que suportem bem o ecossistema de
IA/ML (embeddings, LLMs, avaliação), tipagem estática para reduzir erros, documentação de API
automática, e um caminho maduro de testes.

## 2. Decisão

Adotar **Python 3.12** (gerenciado via `uv`, que provisiona seu próprio interpretador,
independente do Python do sistema) e **FastAPI** para a camada de API, com **Pydantic** para
validação e **pydantic-settings** para configuração centralizada.

## 3. Justificativa

- Ecossistema de IA/ML maduro (sentence-transformers, tiktoken, clientes de LLM) — decisivo
  para os blocos seguintes (chunking, embeddings, geração).
- Integração nativa do FastAPI com tipagem via Pydantic, geração automática de documentação
  OpenAPI (`/docs`), suporte assíncrono e alta testabilidade via `TestClient`/`httpx`.
- `uv` resolve o descompasso entre a versão de Python exigida pelo projeto (3.12) e a
  disponível no ambiente de desenvolvimento (3.11), sem exigir instalação manual de um
  interpretador de sistema.

## 4. Alternativas consideradas

- **Flask**: rejeitado — exigiria composição manual de validação, documentação de API e
  suporte assíncrono que o FastAPI já oferece nativamente.
- **Django**: rejeitado — mais pesado do que o necessário para uma API RAG.
- **Node.js**: rejeitado — ecossistema de IA/ML menos maduro para os requisitos deste projeto.
- **Java/Spring Boot**: rejeitado — overhead de integração desnecessário para o escopo do MVP.

## 5. Consequências

### ✅ Positivas
- Documentação de API interativa gerada automaticamente (`/docs`).
- Validação de entrada declarativa via Pydantic reduz uma classe inteira de bugs.
- Testes rápidos e determinísticos via `TestClient`, sem precisar de um servidor real rodando.

### ⚠️ Negativas
- Nenhuma identificada até o momento neste bloco.

## 6. Considerações de segurança

A escolha do framework não garante segurança por si só — ainda exige disciplina de tipagem,
validação de entrada em cada rota, revisão de dependências (`pip-audit`, planejado para o
Bloco 4) e gestão cuidadosa de segredos (`.env` nunca commitado — ver `.gitignore`).

## 7. Critérios de revisão

Nenhum gatilho de revisão identificado neste bloco.

## 8. Status

Accepted.
