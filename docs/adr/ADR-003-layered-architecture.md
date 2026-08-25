# ADR-003 — Arquitetura em Camadas e Separação de Responsabilidades

`Status: Accepted` · `Data: 2026-08-24` · `Projeto: Corporate Knowledge Assistant`

## 1. Contexto

O sistema combina uma API HTTP, regras de negócio (validação de fontes, ingestão, e nos
próximos blocos: retrieval, geração), e detalhes técnicos substituíveis (PostgreSQL, modelos
de embedding, provedores de LLM). Misturar essas responsabilidades em um único módulo
dificulta testes, aumenta o acoplamento a tecnologias específicas e torna decisões de
segurança implícitas em vez de explícitas.

## 2. Decisão

Adotar uma arquitetura em camadas, parcialmente inspirada em Clean Architecture (sem adotar
todas as suas abstrações, para evitar complexidade desnecessária):

```
api → application → domain → infrastructure
```

- **`api/`**: apenas HTTP — rotas, autenticação, validação de entrada, serialização, códigos
  de status. Sem lógica de negócio.
- **`application/`**: orquestra casos de uso (`ValidateSource`, `IngestDocument`, e futuros
  `AskKnowledgeBase`, `EvaluateRAG`).
- **`domain/`**: conceitos centrais (`Document`, `Source`, e futuros `Chunk`, `User`, `Query`,
  `Answer`) e suas abstrações de repositório — não depende de FastAPI, SQLAlchemy ou qualquer
  detalhe de infraestrutura.
- **`infrastructure/`**: implementações concretas — PostgreSQL (`SqlAlchemyDocumentRepository`),
  arquivos (`YamlSourceRepository`), e futuramente LLM e modelo de embedding.
- **`core/`**: configuração (`Settings`) e utilidades transversais.
- **`observability/`**: logging estruturado e middleware de contexto de requisição.

## 3. Justificativa

- Reduz o acoplamento entre regras de negócio e detalhes técnicos substituíveis (LLMs,
  modelos de embedding, estratégias de retrieval, bancos de dados).
- Aumenta a testabilidade: os testes unitários deste bloco (`tests/unit/test_validate_source.py`,
  `test_ingest_document.py`) usam repositórios em memória, sem precisar de Docker ou rede.
- Torna decisões de segurança explícitas em código de aplicação determinístico, nunca
  implícitas no comportamento de um LLM.

## 4. Alternativas consideradas

- **Monolito baseado em rotas** (lógica de negócio direto nos handlers FastAPI): rejeitado —
  mistura responsabilidades e dificulta testes sem subir a API inteira.
- **Microsserviços**: rejeitado para o MVP — complexidade prematura.
- **Clean Architecture completa** (com todos os seus círculos e abstrações): adotada apenas
  parcialmente, para evitar abstrações que não trazem benefício concreto nesta fase.

## 5. Consequências

### ✅ Positivas
- Casos de uso testáveis isoladamente de FastAPI e PostgreSQL.
- Troca de implementações de infraestrutura (ex.: outro banco, outro provedor de LLM) sem
  tocar `domain/` ou `application/`.

### ⚠️ Negativas
- Mais arquivos e indireção do que um script único — custo aceito em troca de testabilidade e
  clareza de responsabilidade.

## 6. Considerações de segurança

Decisões de segurança críticas (autorização, validação) nunca devem depender apenas do
comportamento probabilístico de um LLM — devem ser código de aplicação determinístico nas
camadas `application`/`domain`, verificável e testável.

## 7. Critérios de revisão

Revisar se a separação em camadas começar a gerar indireção sem benefício real (ex.: casos de
uso triviais que só repassam chamadas) — nesse caso, simplificar.

## 8. Status

Accepted.
