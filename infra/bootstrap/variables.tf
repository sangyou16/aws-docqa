variable "project" {
  type    = string
  default = "docqa"
}

variable "region" {
  type    = string
  default = "ap-southeast-1"
}

variable "github_repo" {
  description = "GitHub repository allowed to deploy, as owner/name."
  type        = string
  validation {
    condition     = can(regex("^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", var.github_repo))
    error_message = "Use the form owner/name."
  }
}

variable "github_branch" {
  type    = string
  default = "main"
}

variable "tf_state_bucket" {
  description = "S3 bucket holding Terraform state (the same one passed to terraform init)."
  type        = string
}

variable "create_github_oidc_provider" {
  description = "Set false if the account already has the token.actions.githubusercontent.com provider."
  type        = bool
  default     = true
}
