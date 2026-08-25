# Infrastructure as Code

Real, syntactically-correct Terraform for an AWS deployment (VPC + RDS/pgvector +
ECS Fargate + ALB) — matching the roadmap's "container-first + lean cloud
deployment" recommendation (§5–6). See ADR-013 for why AWS/ECS specifically.

## Real status: scaffolding, never applied

**No cloud account exists for this project.** This module tree is written to
be structurally correct and ready to `terraform plan`/`apply` against a real
AWS account, but it has never been applied, and doing so would incur real
cost. Do not run `terraform apply` against these environments without first:

1. Provisioning a real AWS account and configuring credentials.
2. Filling in a real `terraform.tfvars` from the `.example` in each
   environment directory (never commit the filled copy).
3. Configuring a real remote state backend (S3 + DynamoDB lock table) —
   commented out in each `environments/*/main.tf` `terraform {}` block,
   deliberately left unset since no such backend exists yet.
4. Obtaining an ACM certificate ARN for the ALB's HTTPS listener
   (`modules/application/main.tf`'s `aws_lb_listener.https` leaves
   `certificate_arn` unset on purpose — never hardcode one here).

`terraform validate` was not run against this scaffolding in this
environment (`terraform` is not installed on this machine, and installing it
solely to validate code that will never be applied here was judged lower
value than documenting this plainly — see `docs/release-gate/PROGRESS.md`,
Block 4). The HCL is written to standard module conventions and cross-checked
by hand against each resource's real, current provider schema.

## Structure

```
infra/
├── modules/
│   ├── networking/    # VPC, public/private subnets, NAT, security groups
│   ├── database/      # RDS PostgreSQL 16 (pgvector-capable)
│   └── application/   # ECS Fargate service + ALB, SSM-backed secrets
└── environments/
    ├── staging/        # single AZ RDS, 1 task
    └── production/     # multi-AZ RDS, 2 tasks, deletion protection
```

## One manual step Terraform does not cover

`aws_db_instance` provisions the RDS instance itself; it does **not** run
`CREATE EXTENSION vector;` against the database. After the first real
`terraform apply`, that has to be run once by hand (or from a one-off
migration job) — same requirement as the local `docker-compose.yml` `db`
service, which handles it via `docker/postgres/init.sql` instead.

## Secrets

`database_url`, `jwt_secret_key`, and `anthropic_api_key` are written into
AWS SSM Parameter Store as `SecureString`s by the `application` module and
injected into the ECS task via `secrets`, never as plain task-definition
environment variables — the same "secrets never in plaintext" rule ADR-009
established for the image itself, extended to the deployment layer.
