# Corporate Knowledge Assistant

Um sistema RAG (Retrieval-Augmented Generation) corporativo: perguntas e
respostas autenticadas, com controle de acesso por papel e por documento,
sobre uma base documental governada — com citações, abstenção quando não
há evidência suficiente, e observabilidade/auditabilidade completas.

**Status: `v1.0.0`.** Construído incrementalmente em quatro blocos, cada
um fechado com evidência real de comando executado, não checkmarks
aspiracionais — o log completo de evidências, bloco a bloco, está em
[`docs/release-gate/PROGRESS.md`](docs/release-gate/PROGRESS.md), e a
decisão de release consolidada está em
[`docs/release-gate/RELEASE_GATE_v1.0.0.md`](docs/release-gate/RELEASE_GATE_v1.0.0.md).

Esse documento de release gate é deliberadamente honesto, inclusive onde
não está tudo limpo: uma verificação real de qualidade de avaliação
(`citation_accuracy`) falha atualmente contra o golden dataset, por um
motivo específico, entendido e documentado — e essa falha foi mantida em
vez de resolvida afrouxando um limiar, porque isso teria enfraquecido
silenciosamente a garantia real do sistema contra alucinação. Vários
outros defeitos reais foram encontrados e corrigidos da mesma forma, em
cada etapa do projeto, até a configuração de uma `ANTHROPIC_API_KEY` real
pela primeira vez, já depois da tag de release. Esse rastro é o ponto
central: toda afirmação neste repositório é sustentada por algo que
realmente foi executado, não apenas escrito.

## O que está implementado

- FastAPI + PostgreSQL/pgvector, observabilidade estruturada (structlog
  com correlação de requisições), um Registro de Fontes governado que
  controla a ingestão de documentos.
- Chunking + embeddings reais via sentence-transformers, retrieval híbrido
  (cosseno via pgvector + busca full-text no PostgreSQL, fundidos via RRF)
  com reranking por cross-encoder.
- Um orquestrador RAG com resposta fundamentada (`POST /ask`), validação
  de citações, confiança baseada em regras e abstenção quando a evidência
  é insuficiente — geração real via Anthropic Claude atrás de uma
  interface abstrata `LLMProvider` (fallback `FakeLLMProvider` quando
  nenhuma chave está configurada).
- Autenticação JWT + hashing de senha com Argon2id, RBAC + controle de
  acesso real por papel e por documento (o teste de autorização
  EMPLOYEE-vs-MANAGEMENT do roadmap é real e está passando), rate
  limiting por usuário.
- Um framework de avaliação RAG com um Golden Dataset real
  (`scripts/evaluate.py`) e pontuação real via LLM-as-judge.
- Tracing distribuído real (OpenTelemetry → Jaeger) e métricas
  (Prometheus → Grafana, ambos provisionados via arquivo, não configurados
  manualmente).
- Build Docker multi-stage, não-root; 4 workflows do GitHub Actions (CI,
  varredura de segurança, build/scan de container, release por tag);
  scaffolding Terraform para AWS em staging/produção (`infra/`).
- Um conjunto completo de documentação — arquitetura, referência de API,
  controles de segurança, metodologia de avaliação, runbook de operações —
  em [`docs/`](docs/), e 15 ADRs reais em [`docs/adr/`](docs/adr/).

## Como rodar

```bash
# 1. Instalar dependências (uv gerencia sua própria instalação do Python 3.12)
pip install uv
uv python install 3.12
uv sync

# 2. Subir PostgreSQL + pgvector
docker compose up -d db

# 3. Aplicar as migrations
cp .env.example .env
uv run alembic upgrade head

# (opcional) adicione uma ANTHROPIC_API_KEY real no .env para geração real em /ask —
# sem ela, /ask continua funcionando (retrieval, ACL, abstenção), usando
# FakeLLMProvider em vez de uma chamada real ao modelo.

# 4. Criar um usuário (veja scripts/seed_users.py) e fazer login
uv run python scripts/seed_users.py
curl -X POST http://127.0.0.1:8000/auth/login -d '{"username": "employee.test", "password": "..."}'

# 5. Rodar a API
uv run uvicorn cka.main:app --reload

# 6. Verificar que está no ar, e então perguntar algo (com o token do passo 4)
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/health/ready
curl -X POST http://127.0.0.1:8000/ask \
  -H "Authorization: Bearer <token>" -d '{"query": "sua pergunta aqui"}'
```

> Rodando a stack completa via `docker compose up` em vez de `uvicorn`
> diretamente? A API é publicada na porta `8010` do host (não 8000), o
> Postgres na `5434` (não 5432), a UI do Jaeger na `16686`, o Prometheus na
> `9090`, o Grafana na `3000` — veja a nota sobre portas em
> `docs/release-gate/PROGRESS.md` para entender por que as portas fogem do
> padrão.

## Testes

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src tests scripts
uv run pytest --cov=src/cka --cov-report=term-missing
```

Os testes unitários (`tests/unit`) rodam sem Docker. Os testes de
integração (`tests/integration`), de segurança (`tests/security`) e de
observabilidade (`tests/observability`) exigem `docker compose up -d db`
primeiro, e rodam contra um banco dedicado `cka_test` (nunca o banco onde
vivem os dados reais de desenvolvimento/demo — veja `tests/conftest.py`).

## Avaliação

```bash
uv run python scripts/evaluate.py
```

Roda o Golden Dataset real (`data/evaluation/`) contra o retriever e o
orquestrador RAG reais, grava `reports/evaluation_latest.{json,md}`, e
retorna código de saída diferente de zero se o gate de qualidade
(`Settings.evaluation_min_*`) for violado. Veja
[`docs/evaluation/`](docs/evaluation/) para a metodologia e os resultados
reais e atuais — incluindo a verificação que falha honestamente.

## Deployment

`infra/` contém Terraform real e estruturalmente correto (AWS: VPC,
RDS/pgvector, ECS Fargate, ALB) para `staging`/`production` — escrito e
revisável, mas nunca aplicado (não há conta cloud por trás deste projeto;
veja
[`docs/adr/ADR-013-production-deployment-and-release-engineering.md`](docs/adr/ADR-013-production-deployment-and-release-engineering.md)
e [`infra/README.md`](infra/README.md) para entender exatamente o que
isso significa e o que não significa).

## Decisões de arquitetura

Veja [`docs/adr/`](docs/adr/) para os 15 Architecture Decision Records que
regem este projeto — governança de fontes, escolha de banco de dados,
arquitetura em camadas, escolha de framework, hardening de segurança,
avaliação, observabilidade, CI/CD, deployment e governança de
documentação.
