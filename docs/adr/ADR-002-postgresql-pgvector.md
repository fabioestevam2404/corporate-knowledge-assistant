# ADR-002 — Adoção do PostgreSQL com pgvector

`Status: Accepted` · `Data: 2026-08-24` · `Projeto: Corporate Knowledge Assistant`

## 1. Contexto

Um sistema RAG precisa armazenar tanto dados relacionais convencionais (documentos, fontes,
usuários, auditoria) quanto vetores de embedding para busca por similaridade. Rodar um banco
relacional e um banco vetorial dedicado separadamente aumenta a complexidade operacional do
MVP sem benefício claro nesta fase.

## 2. Decisão

Adotar **PostgreSQL 16** como armazenamento primário, com a extensão **pgvector** para
embeddings — uma única plataforma unificada para dados relacionais, metadados, vetores e,
futuramente, registros de auditoria. Em desenvolvimento, roda via Docker Compose
(`pgvector/pgvector:pg16`).

## 3. Justificativa

- Reduz a complexidade operacional do MVP: um único banco para operar, fazer backup e
  monitorar.
- Permite consultas combinadas de vetor + metadados + autorização em uma única query SQL,
  o que é decisivo para aplicar o controle de acesso **antes** da busca vetorial (ver Gate 4 —
  Security no Release Gate).
- SQLAlchemy 2.x + Alembic já fornecem um caminho maduro de migração de schema.

## 4. Alternativas consideradas

- **ChromaDB, Qdrant, Pinecone**: não selecionados para o MVP — adiados, não descartados, para
  reavaliação em escala.
- **Banco relacional separado do banco vetorial**: adiado — complexidade operacional
  desnecessária nesta fase.

## 5. Consequências

### ✅ Positivas
- Um único ponto de operação, backup e observabilidade.
- Consultas híbridas (vetor + metadados + ACL) em uma única transação.

### ⚠️ Negativas
- Pode exigir otimização ou um banco vetorial dedicado em escalas muito maiores.

## 6. Considerações de segurança

O usuário de aplicação usado pela API deve ter privilégio mínimo (não superusuário) e a rede
do banco não deve ser exposta diretamente à internet — ver `docker-compose.yml`, onde `db` só
é alcançável pela rede interna do Compose e pela porta mapeada localmente para desenvolvimento.

## 7. Critérios de revisão

Revisar se o volume de embeddings ou a latência de busca por similaridade ultrapassar o que
pgvector suporta com performance aceitável em produção.

## 8. Status

Accepted.
