variable "environment" {
  type        = string
  description = "Environment name (staging/production), used for resource naming/tagging."
}

variable "vpc_cidr" {
  type        = string
  default     = "10.20.0.0/16"
  description = "CIDR block for the VPC."
}

variable "az_count" {
  type        = number
  default     = 2
  description = "Number of availability zones to spread public/private subnets across."
}

data "aws_availability_zones" "available" {
  state = "available"
}

resource "aws_vpc" "this" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name        = "cka-${var.environment}-vpc"
    Environment = var.environment
    Project     = "corporate-knowledge-assistant"
  }
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id

  tags = {
    Name = "cka-${var.environment}-igw"
  }
}

# Public subnets: only the ALB lives here.
resource "aws_subnet" "public" {
  count             = var.az_count
  vpc_id            = aws_vpc.this.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index)
  availability_zone = data.aws_availability_zones.available.names[count.index]
  # No EC2 instances launch directly in this subnet (only the ALB, which
  # gets its own AWS-managed public IP regardless of this setting) — so
  # auto-assigning public IPs here has no upside and trips AVD-AWS-0164.
  map_public_ip_on_launch = false

  tags = {
    Name = "cka-${var.environment}-public-${count.index}"
    Tier = "public"
  }
}

# Private subnets: ECS tasks and the RDS instance live here — never
# internet-routable directly, matching ADR-013's "app + db not publicly
# reachable except through the ALB" decision.
resource "aws_subnet" "private" {
  count             = var.az_count
  vpc_id            = aws_vpc.this.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index + var.az_count)
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name = "cka-${var.environment}-private-${count.index}"
    Tier = "private"
  }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.this.id
  }

  tags = {
    Name = "cka-${var.environment}-public-rt"
  }
}

resource "aws_route_table_association" "public" {
  count          = var.az_count
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_eip" "nat" {
  domain = "vpc"

  tags = {
    Name = "cka-${var.environment}-nat-eip"
  }
}

# Single NAT gateway (not one per AZ) — deliberate lean-cost tradeoff for a
# project of this size, per ADR-013. Revisit if production traffic ever
# justifies AZ-redundant NAT.
resource "aws_nat_gateway" "this" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public[0].id

  tags = {
    Name = "cka-${var.environment}-nat"
  }
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.this.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.this.id
  }

  tags = {
    Name = "cka-${var.environment}-private-rt"
  }
}

resource "aws_route_table_association" "private" {
  count          = var.az_count
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}

resource "aws_security_group" "alb" {
  name_prefix = "cka-${var.environment}-alb-"
  vpc_id      = aws_vpc.this.id

  ingress {
    description = "HTTPS from the internet"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # No inline egress block here: the ALB->app rule below references this SG
  # AND aws_security_group.app, and app's ingress already references this
  # SG back — an inline egress block on either side creates a dependency
  # cycle (Terraform: "Cycle: ...alb, ...app, ...db"). A standalone
  # aws_vpc_security_group_egress_rule breaks the cycle because it's not
  # part of either security group resource's own body.

  tags = {
    Name = "cka-${var.environment}-alb-sg"
  }
}

# The ALB only ever forwards to the app tier on 8000 — no reason for
# unrestricted egress (was tripping AVD-AWS-0104). Split out from
# aws_security_group.alb to avoid an alb<->app dependency cycle (see
# comment above).
resource "aws_vpc_security_group_egress_rule" "alb_to_app" {
  security_group_id            = aws_security_group.alb.id
  description                  = "To the app tier only"
  from_port                    = 8000
  to_port                      = 8000
  ip_protocol                  = "tcp"
  referenced_security_group_id = aws_security_group.app.id
}

resource "aws_security_group" "app" {
  name_prefix = "cka-${var.environment}-app-"
  vpc_id      = aws_vpc.this.id

  ingress {
    description     = "From the ALB only"
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  # No inline egress to the db SG here either — same alb<->app cycle
  # problem, this time between app and db (db's ingress already references
  # this SG back). See aws_vpc_security_group_egress_rule.app_to_db below.

  # HTTPS out is still 0.0.0.0/0 by necessity — the Anthropic API and any
  # package/OS update endpoints are arbitrary external hosts, not something
  # a security-group reference can scope. Narrowed to port 443 only (was a
  # blanket protocol=-1/all-ports rule tripping AVD-AWS-0104); this is the
  # documented, accepted shape of that risk, not an oversight.
  # trivy:ignore:AVD-AWS-0104
  egress {
    description = "HTTPS out (Anthropic API, package/OS updates)"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "cka-${var.environment}-app-sg"
  }
}

resource "aws_security_group" "db" {
  name_prefix = "cka-${var.environment}-db-"
  vpc_id      = aws_vpc.this.id

  ingress {
    description     = "Postgres from the app tier only"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
  }

  # No egress block: RDS doesn't need to initiate outbound connections for
  # normal query serving — the previous blanket 0.0.0.0/0 rule had no
  # legitimate purpose here (was tripping AVD-AWS-0104). Terraform/AWS
  # default with no egress block is "deny all outbound".

  tags = {
    Name = "cka-${var.environment}-db-sg"
  }
}

# Postgres, app tier only — split out from aws_security_group.app to avoid
# an app<->db dependency cycle (see comments on that resource).
resource "aws_vpc_security_group_egress_rule" "app_to_db" {
  security_group_id            = aws_security_group.app.id
  description                  = "Postgres, app tier only"
  from_port                    = 5432
  to_port                      = 5432
  ip_protocol                  = "tcp"
  referenced_security_group_id = aws_security_group.db.id
}

output "vpc_id" {
  value = aws_vpc.this.id
}

output "public_subnet_ids" {
  value = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  value = aws_subnet.private[*].id
}

output "alb_security_group_id" {
  value = aws_security_group.alb.id
}

output "app_security_group_id" {
  value = aws_security_group.app.id
}

output "db_security_group_id" {
  value = aws_security_group.db.id
}
