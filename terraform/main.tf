terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket       = "project-thapanstate-bucket" # <-- your bucket name
    key          = "statefile/terraform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project   = var.project_name
      ManagedBy = "terraform"
    }
  }
}

module "app_server" {
  source = "./modules/app-server"

  project_name  = var.project_name
  instance_type = var.instance_type
  vpc_id        = module.network.vpc_id
  subnet_id     = module.network.public_subnet_id
}

module "cicd_access" {
  source = "./modules/ci-cd-access"

  project_name = var.project_name
  region       = var.region
  github_repo  = var.github_repo
}

module "notifications" {
  source = "./modules/notifications"

  project_name     = var.project_name
  alert_email      = var.alert_email
  table_stream_arn = module.app_server.table_stream_arn
}

module "network" {
  source = "./modules/network"

  project_name = var.project_name
  region       = var.region

}
# ---------- $1 budget alert (single resource, so no module needed) ----------
resource "aws_budgets_budget" "learning" {
  name         = "${var.project_name}-budget"
  budget_type  = "COST"
  limit_amount = "1"
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.alert_email]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [var.alert_email]
  }
}