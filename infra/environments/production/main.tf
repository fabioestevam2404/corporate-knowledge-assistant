terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Real deployments should configure a real remote backend (S3 + DynamoDB
  # lock table) here — left unset in this scaffolding since no such backend
  # exists yet (no cloud account provisioned, per ADR-013/PROGRESS.md).
  # backend "s3" {}
}

provider "aws" {
  region = var.aws_region
}

module "networking" {
  source = "../../modules/networking"

  environment = "production"
}

module "database" {
  source = "../../modules/database"

  environment           = "production"
  private_subnet_ids    = module.networking.private_subnet_ids
  db_security_group_id  = module.networking.db_security_group_id
  db_password            = var.db_password
  # Production-specific, differing from staging: cross-AZ failover and a
  # larger instance class, per ADR-013.
  multi_az                = true
  instance_class           = "db.t4g.medium"
}

module "application" {
  source = "../../modules/application"

  environment            = "production"
  vpc_id                  = module.networking.vpc_id
  public_subnet_ids       = module.networking.public_subnet_ids
  private_subnet_ids      = module.networking.private_subnet_ids
  alb_security_group_id   = module.networking.alb_security_group_id
  app_security_group_id   = module.networking.app_security_group_id
  container_image         = var.container_image
  # Two tasks, not one — production shouldn't run single-replica, unlike
  # staging.
  desired_count             = 2
  database_url              = "postgresql+psycopg://${module.database.db_name}:${var.db_password}@${module.database.endpoint}/${module.database.db_name}"
  jwt_secret_key             = var.jwt_secret_key
  anthropic_api_key          = var.anthropic_api_key
}

output "alb_dns_name" {
  value = module.application.alb_dns_name
}

output "database_endpoint" {
  value = module.database.endpoint
}
