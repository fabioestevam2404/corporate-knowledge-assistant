# RDS PostgreSQL with pgvector. pgvector ships as a supported extension on
# RDS Postgres 16 (CREATE EXTENSION vector; still has to run once against the
# real database — this module provisions the instance, not the extension
# itself; see infra/README.md for the manual/bootstrap step).

variable "environment" {
  type = string
}

variable "private_subnet_ids" {
  type = list(string)
}

variable "db_security_group_id" {
  type = string
}

variable "instance_class" {
  type        = string
  default     = "db.t4g.small"
  description = "Small/burstable by default — matches the roadmap's 'lean, not over-provisioned' guidance. Bump for production if real load demands it."
}

variable "allocated_storage_gb" {
  type    = number
  default = 20
}

variable "engine_version" {
  type    = string
  default = "16.4"
}

variable "db_name" {
  type    = string
  default = "cka"
}

variable "db_username" {
  type    = string
  default = "cka"
}

variable "db_password" {
  type        = string
  sensitive   = true
  description = "Real deployments MUST pass this via a secret manager / CI secret, never a checked-in .tfvars file."
}

variable "multi_az" {
  type        = bool
  default     = false
  description = "false for staging (cost), should be true for production per ADR-013."
}

resource "aws_db_subnet_group" "this" {
  name       = "cka-${var.environment}-db-subnets"
  subnet_ids = var.private_subnet_ids

  tags = {
    Name = "cka-${var.environment}-db-subnet-group"
  }
}

resource "aws_db_instance" "this" {
  identifier     = "cka-${var.environment}"
  engine         = "postgres"
  engine_version = var.engine_version
  instance_class = var.instance_class

  allocated_storage = var.allocated_storage_gb
  storage_type      = "gp3"
  storage_encrypted = true

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [var.db_security_group_id]

  multi_az                = var.multi_az
  publicly_accessible     = false
  backup_retention_period = var.environment == "production" ? 7 : 1
  skip_final_snapshot     = var.environment != "production"
  deletion_protection     = var.environment == "production"

  tags = {
    Name        = "cka-${var.environment}-db"
    Environment = var.environment
    Project     = "corporate-knowledge-assistant"
  }
}

output "endpoint" {
  value = aws_db_instance.this.endpoint
}

output "db_name" {
  value = aws_db_instance.this.db_name
}
