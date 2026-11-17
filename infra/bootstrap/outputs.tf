output "deploy_role_arn" {
  description = "Put this in the GitHub repo variable AWS_DEPLOY_ROLE_ARN."
  value       = aws_iam_role.deploy.arn
}

output "lambda_boundary_arn" {
  value = aws_iam_policy.lambda_boundary.arn
}
