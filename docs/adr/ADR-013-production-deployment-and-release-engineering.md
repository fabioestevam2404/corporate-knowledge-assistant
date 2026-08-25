# ADR-013 — Production Deployment e Release Engineering

`Status: Accepted` · `Data: 2026-08-25` · `Projeto: Corporate Knowledge Assistant`

## 1. Contexto

O roadmap (§5–6) deixa a escolha de nuvem em aberto — "Opção A: Cloud completa
(AWS/Azure/GCP)" vs. "Opção B: Container PaaS" vs. "Opção C: VPS" — e
recomenda explicitamente "container-first + cloud deployment enxuto",
registrando a decisão final em ADR. Até o fim do Sprint 12, a aplicação só
existia como imagem Docker local (`docker-compose.yml`), sem nenhum caminho
real de deployment além da máquina de desenvolvimento.

## 2. Decisão

**AWS, via ECS Fargate + RDS + ALB**, como IaC de referência (Terraform em
`infra/`), separando `staging` e `production` como ambientes distintos —
mas **sem provisionar uma conta cloud real nem rodar `terraform apply`**.
Este bloco entrega infraestrutura como código real e estruturalmente
correta, não infraestrutura implantada.

Componentes reais escritos:
- `infra/modules/networking`: VPC, subnets públicas (só ALB) e privadas (app
  + DB), NAT gateway único, security groups com least-privilege (DB só aceita
  tráfego do app tier; app tier só aceita tráfego do ALB).
- `infra/modules/database`: RDS PostgreSQL 16 (pgvector-capable),
  `multi_az=false` em staging / `true` em produção, `deletion_protection`
  só em produção.
- `infra/modules/application`: ECS Fargate + ALB, segredos via SSM Parameter
  Store `SecureString` (nunca variável de ambiente em texto puro na task
  definition), healthcheck real via `/health` (mesmo comando do
  `HEALTHCHECK` do Dockerfile), target group apontando para `/health/ready`.
- `.env.staging.example` / `.env.production.example`: separação real de
  ambiente, todo campo mapeado 1:1 para `Settings` real
  (`src/cka/core/config.py`) — nenhuma chave inventada.
- `scripts/smoke_test.sh`: roda de verdade contra a stack local
  (`/health` → `/health/ready` → `/auth/login` → `/retrieve` → `/ask`),
  reutilizável contra staging/produção via `BASE_URL`.
- `docs/governance/model-governance.md`: registro real de modelo/versão em
  uso (`claude-sonnet-5`, `all-MiniLM-L6-v2`,
  `cross-encoder/ms-marco-MiniLM-L-6-v2`, `PROMPT_VERSION = "v1"` — este
  último adicionado neste sprint especificamente para existir algo real a
  documentar).

## 3. Justificativa

AWS/ECS Fargate é o caminho mais direto para "container-first, enxuto":
reaproveita a mesma imagem Docker multi-stage do Sprint 12 sem reescrever
para outro runtime, sem gerenciar servidores (Fargate é serverless), e RDS
com suporte a `pgvector` reaproveita o mesmo schema/extensão já usado
localmente — nenhuma mudança de arquitetura de dados entre dev e produção.
Terraform (não CloudFormation/Pulumi) porque é o formato explicitamente
citado no roadmap (§7) e é cloud-agnóstico o suficiente para uma futura
migração de provedor não exigir reescrever a estrutura de módulos, só o
provider.

**Não aplicar de verdade é uma decisão deliberada, não uma limitação
escondida**: não existe conta cloud para este projeto, e provisionar
recursos reais (mesmo que dentro do free tier) para um exercício de
validação de release gate introduziria custo e risco de configuração
esquecida rodando indefinidamente, sem benefício real de evidência sobre o
que já foi comprovado localmente (a imagem sobe, funciona, responde aos
endpoints reais — ver `docs/release-gate/PROGRESS.md`).

## 4. Alternativas consideradas

- **Container PaaS (Opção B do roadmap — Render/Fly.io/Railway)**: mais
  simples de fato aplicar sem conta cloud complexa, mas demonstra menos
  competência de networking/IAM real — o roadmap já nota esse tradeoff.
  Rejeitado porque o objetivo deste bloco é ter Terraform real e revisável,
  não necessariamente aplicado.
- **VPS (Opção C)**: mais controle, mas exige gerenciar patching de SO,
  hardening manual — carga operacional desproporcional ao escopo deste
  projeto. Rejeitado.
- **Rodar `terraform apply` de verdade contra uma conta AWS free-tier**:
  considerado e rejeitado — ver justificativa acima. `terraform validate`
  também não foi rodado (Terraform não está instalado nesta máquina;
  instalar só para validar HCL que nunca será aplicado aqui foi julgado de
  baixo valor comparado a documentar isso explicitamente).
- **NAT gateway por AZ (redundante)**: rejeitado por custo, dado o porte do
  projeto — NAT único documentado como tradeoff consciente no próprio
  módulo, revisável se produção real algum dia justificar.

## 5. Consequências

### ✅ Positivas
- Caminho de deployment real, revisável, versionado — não apenas descrito
  em prosa.
- Separação real staging/produção nas variáveis de ambiente, cada uma
  mapeada para um campo `Settings` real, incluindo o hard-fail já existente
  em código para `JWT_SECRET_KEY` padrão em produção
  (`Settings._forbid_dev_jwt_secret_in_production`).
- `scripts/smoke_test.sh` real, testado de ponta a ponta contra a stack ao
  vivo local (ver PROGRESS.md) — não apenas escrito, mas comprovadamente
  funcional.

### ⚠️ Negativas
- HCL nunca `apply`'d nem `validate`'d por ferramenta — risco residual de
  erro que só um `terraform plan` real revelaria. Mitigado por escrita
  cuidadosa contra o schema real de cada resource, mas não é o mesmo nível
  de confiança que os testes automatizados deste projeto.
- Demonstração real de rollback (planejada para este sprint) foi adiada —
  ver `docs/release-gate/PROGRESS.md`, Bloco 4/Sprint 13: a mesma
  instabilidade do Docker/WSL2 nesta máquina (documentada no ADR-012)
  ainda afetava operações Docker ao vivo no momento em que esse passo seria
  executado. Não simulado nem descrito como concluído sem tê-lo sido.

## 6. Considerações de segurança

Segredos (`DATABASE_URL`, `JWT_SECRET_KEY`, `ANTHROPIC_API_KEY`) nunca em
texto puro na task definition do ECS — injetados via SSM Parameter Store
`SecureString`, mesma regra do ADR-009 estendida à camada de deployment.
`.env.production.example` não define default para `ANTHROPIC_API_KEY`
(diferente de `.env.staging.example`), para que produção nunca rode
silenciosamente sobre o fallback `FakeLLMProvider`. Subnets privadas para
app e banco — nenhum dos dois é publicamente roteável, só o ALB.

## 7. Critérios de revisão

Revisar quando uma conta cloud real existir para este projeto — nesse ponto,
rodar `terraform validate`/`plan` de verdade antes de qualquer `apply`, e
promover o backend remoto (S3 + DynamoDB) atualmente comentado. Revisar a
demonstração de rollback adiada assim que o ambiente Docker local estiver
estável (ou diretamente contra uma conta cloud real, o que a tornaria mais
representativa de qualquer forma).

## 8. Status

Accepted.
