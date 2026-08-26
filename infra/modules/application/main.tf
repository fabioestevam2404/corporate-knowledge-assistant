# ECS Fargate service running the real multi-stage image built in
# Dockerfile/docker.yml (published to GHCR by release.yml), behind an ALB.
# Container port 8000 matches the Dockerfile's EXPOSE/CMD — see ADR-012.

variable "environment" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "public_subnet_ids" {
  type = list(string)
}

variable "private_subnet_ids" {
  type = list(string)
}

variable "alb_security_group_id" {
  type = string
}

variable "app_security_group_id" {
  type = string
}

variable "container_image" {
  type        = string
  description = "Full image ref, e.g. ghcr.io/<org>/corporate-knowledge-assistant:v1.0.0 (from release.yml)."
}

variable "task_cpu" {
  type    = string
  default = "1024"
}

variable "task_memory" {
  type    = string
  default = "2048"
}

variable "desired_count" {
  type    = number
  default = 1
}

variable "database_url" {
  type      = string
  sensitive = true
}

variable "jwt_secret_key" {
  type      = string
  sensitive = true
}

variable "anthropic_api_key" {
  type      = string
  sensitive = true
  default   = ""
}

resource "aws_ecs_cluster" "this" {
  name = "cka-${var.environment}"
}

resource "aws_cloudwatch_log_group" "app" {
  name              = "/ecs/cka-${var.environment}"
  retention_in_days = var.environment == "production" ? 30 : 7
}

resource "aws_ecs_task_definition" "app" {
  family                   = "cka-${var.environment}"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([
    {
      name      = "api"
      image     = var.container_image
      essential = true
      portMappings = [
        { containerPort = 8000, protocol = "tcp" }
      ]
      environment = [
        { name = "ENVIRONMENT", value = var.environment },
        { name = "LOG_LEVEL", value = var.environment == "production" ? "WARNING" : "INFO" },
        { name = "OTEL_TRACES_ENABLED", value = "true" },
      ]
      secrets = [
        { name = "DATABASE_URL", valueFrom = aws_ssm_parameter.database_url.arn },
        { name = "JWT_SECRET_KEY", valueFrom = aws_ssm_parameter.jwt_secret_key.arn },
        { name = "ANTHROPIC_API_KEY", valueFrom = aws_ssm_parameter.anthropic_api_key.arn },
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.app.name
          "awslogs-region"        = "us-east-1"
          "awslogs-stream-prefix" = "api"
        }
      }
      healthCheck = {
        command     = ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=3)\" || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
    }
  ])

  tags = {
    Environment = var.environment
    Project     = "corporate-knowledge-assistant"
  }
}

# Secrets injected via SSM Parameter Store (SecureString), never as plain
# task-definition environment variables — matches ADR-009's "secrets never
# in the image, never in plain env" rule extended to the deployment layer.
resource "aws_ssm_parameter" "database_url" {
  name  = "/cka/${var.environment}/database_url"
  type  = "SecureString"
  value = var.database_url
}

resource "aws_ssm_parameter" "jwt_secret_key" {
  name  = "/cka/${var.environment}/jwt_secret_key"
  type  = "SecureString"
  value = var.jwt_secret_key
}

resource "aws_ssm_parameter" "anthropic_api_key" {
  name  = "/cka/${var.environment}/anthropic_api_key"
  type  = "SecureString"
  value = var.anthropic_api_key
}

resource "aws_iam_role" "execution" {
  name = "cka-${var.environment}-ecs-execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "execution_managed" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "execution_ssm" {
  name = "cka-${var.environment}-ssm-read"
  role = aws_iam_role.execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["ssm:GetParameters"]
      Resource = [
        aws_ssm_parameter.database_url.arn,
        aws_ssm_parameter.jwt_secret_key.arn,
        aws_ssm_parameter.anthropic_api_key.arn,
      ]
    }]
  })
}

# Task role: no AWS API calls made from inside the app today — scoped to
# nothing extra beyond the default. Kept separate from the execution role
# (least-privilege: pulling the image/reading secrets is not the same
# permission as anything the app itself might need later).
resource "aws_iam_role" "task" {
  name = "cka-${var.environment}-ecs-task"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

# internal = false is intentional: this is the public API entry point for
# the assistant, not an internal-only service — see aws_lb_listener.https
# below for the HTTPS-only, TLS 1.3 access path. AVD-AWS-0053 flags this
# as a warning to catch *accidental* exposure; here it's the whole point.
# trivy:ignore:AVD-AWS-0053
resource "aws_lb" "this" {
  name                       = "cka-${var.environment}"
  internal                   = false
  load_balancer_type         = "application"
  security_groups            = [var.alb_security_group_id]
  subnets                    = var.public_subnet_ids
  drop_invalid_header_fields = true
}

resource "aws_lb_target_group" "app" {
  name        = "cka-${var.environment}"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    path                = "/health/ready"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    interval            = 30
    timeout             = 5
  }
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.this.arn
  port              = 443
  protocol          = "HTTPS"
  # certificate_arn intentionally left unset — real deployments must supply
  # an ACM cert ARN via a real terraform.tfvars, never hardcoded here.
  ssl_policy = "ELBSecurityPolicy-TLS13-1-2-2021-06"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}

resource "aws_ecs_service" "app" {
  name            = "cka-${var.environment}"
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = var.private_subnet_ids
    security_groups = [var.app_security_group_id]
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.app.arn
    container_name   = "api"
    container_port   = 8000
  }

  # Graceful shutdown: ECS sends SIGTERM and waits before SIGKILL — matches
  # the real, verified behavior in docker-compose.yml (`docker compose stop`
  # already confirmed uvicorn shuts down cleanly on SIGTERM, see PROGRESS.md).
  deployment_minimum_healthy_percent = 100
  deployment_maximum_percent         = 200

  depends_on = [aws_lb_listener.https]
}

output "alb_dns_name" {
  value = aws_lb.this.dns_name
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.this.name
}

output "ecs_service_name" {
  value = aws_ecs_service.app.name
}
