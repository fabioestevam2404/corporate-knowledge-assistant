# Threat Model — Corporate Knowledge Assistant

Seed version written in Block 3 (Sprint 09), against real, implemented mitigations — not
aspirational. The full documentation set (deployment/runbook/DR) lands in Block 4.

## Assets

| ID | Ativo |
|---|---|
| A1 | Documentos corporativos (corpus real: `data/raw/samples/`, governado via `data/sources/registry.yaml`) |
| A2 | Dados pessoais (nenhum PII real neste MVP — corpus é 100% conteúdo placeholder autorado para o projeto) |
| A3 | Informações confidenciais (documentos `access_level: management`, ex.: `SRC-SAMPLE-003`) |
| A4 | Credenciais (senhas de usuário — hash Argon2id; `JWT_SECRET_KEY`) |
| A5 | Prompts (system prompt em `application/rag/prompt_builder.py`) |
| A6 | Respostas geradas |
| A7 | Logs (structlog, JSON) |
| A8 | Tokens JWT emitidos |

## STRIDE

| Ameaça | Exemplo real neste projeto | Mitigação implementada |
|---|---|---|
| Spoofing | Token JWT forjado | Assinatura HS256 verificada (`decode_access_token`); `InvalidTokenError` → 401 |
| Tampering | Documento alterado após ingestão | SHA-256 de integridade (`document_integrity.py`), calculado na ingestão |
| Repudiation | Ação sem rastro | `request_id`/`trace_id` propagado em todo log estruturado; eventos `auth_success`/`auth_failure`/`authorization_denied` |
| Information Disclosure | EMPLOYEE acessando documento MANAGEMENT | `AccessScope` real (ADR-009), testado em `tests/security/test_document_acl.py` |
| Denial of Service | Excesso de requisições | `RateLimiter` (60 req/min/usuário), testado em `tests/security/test_rate_limiting.py` |
| Elevation of Privilege | EMPLOYEE chamando `POST /documents` | `require_permission("documents:write")` → 403, testado em `tests/security/test_authorization_rbac.py` |

## Ameaças específicas de IA

| ID | Ameaça | Risco | Mitigação implementada |
|---|---|---|---|
| T02 | Prompt injection (direto — usuário) | Alto | Isolamento estrutural `<USER_QUERY>`, regras explícitas no system prompt |
| T03 | Prompt injection (indireto — documento) | Alto | Isolamento `<UNTRUSTED_DOCUMENTS>`; documento adversarial real testado (`SRC-SAMPLE-005`) |
| T04 | Data leakage (documento não autorizado no contexto do LLM) | Alto | `AccessScope` aplicado antes da recuperação — nunca pós-filtro |
| T07 | SQL injection via campo `query` | Alto | Queries parametrizadas (SQLAlchemy ORM + `:query_text` bind); testado com payloads reais |
| T09 | Dados sensíveis em logs | Alto | Conteúdo de documentos e prompts completos nunca logados — apenas ids, contagens, durações |
| T10 | Escalação de privilégio via token adulterado | Crítico | Verificação de assinatura + claim `role` obrigatório (`InvalidTokenError` se ausente) |

## Teste crítico de autorização (Release Gate §7)

Documento A (`SRC-SAMPLE-001`, `public`) e Documento B (`SRC-SAMPLE-003`, `management`).
Usuário com role EMPLOYEE pergunta sobre o conteúdo do Documento B:

```
EMPLOYEE → Authentication (JWT real) → Authorization (AccessScope real)
   → ACL Filter (access_level not in {public, internal})
   → X Confidential Document
```

Verificado por `tests/security/test_document_acl.py`, com controles positivos (MANAGER e
ADMIN veem o documento) provando que a exclusão é autorização real, não um bug que esconde o
documento de todos.

## Gaps conhecidos (documentados, não escondidos)

- Sem endpoint de auditoria persistente (`GET /audit`) — eventos de segurança ficam em logs
  estruturados. Ver `docs/release-gate/PROGRESS.md`, seção Bloco 3.
- Rate limiting não sobrevive a múltiplas instâncias (in-memory, single-process).
- Sem detecção automática de PII — aceitável neste MVP porque o corpus é inteiramente
  conteúdo placeholder sem dados pessoais reais.
