variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "container_image" {
  type        = string
  description = "e.g. ghcr.io/<org>/corporate-knowledge-assistant:v1.0.0"
}

variable "db_password" {
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
}
