# The application: Lambda (FastAPI via Mangum) behind an API Gateway HTTP API.
# Applied by hand the first time, then by GitHub Actions using the OIDC deploy role.

terraform {
  required_version = ">= 1.10"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.0" }
  }
  backend "s3" {
    key          = "docqa/app.tfstate"
    region       = "ap-southeast-1"
    encrypt      = true
    use_lockfile = true
    # bucket is passed at init: terraform init -backend-config="bucket=<your-state-bucket>"
  }
}

provider "aws" {
  region = var.region
  default_tags { tags = { Project = var.project } }
}

data "aws_caller_identity" "me" {}

locals {
  account      = data.aws_caller_identity.me.account_id
  name         = "${var.project}-api"
  boundary_arn = "arn:aws:iam::${local.account}:policy/${var.project}-lambda-boundary" # from bootstrap stack
}
