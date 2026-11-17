# What the CI deploy role may do: manage exactly the resources of the app stack.
# Resource ARNs are pinned to the "<project>-" name prefix wherever the service allows it.

locals {
  lambda_role_arn = "arn:aws:iam::${local.account}:role/${var.project}-lambda-*"
  boundary_arn    = aws_iam_policy.lambda_boundary.arn
}

data "aws_iam_policy_document" "deploy" {
  # Terraform state for the app stack only (lock file lives next to the state object).
  statement {
    sid       = "StateList" # unscoped by prefix: the backend also lists the workspace prefix (env:/)
    actions   = ["s3:ListBucket"]
    resources = ["arn:aws:s3:::${var.tf_state_bucket}"]
  }
  statement {
    sid       = "StateObjects"
    actions   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
    resources = ["arn:aws:s3:::${var.tf_state_bucket}/docqa/app.tfstate*"]
  }

  # Lambda function(s) named <project>-*
  statement {
    sid       = "Lambda"
    actions   = ["lambda:*"]
    resources = ["arn:aws:lambda:${var.region}:${local.account}:function:${var.project}-*"]
  }

  # IAM: read/delete Lambda roles, and create/change them only with the boundary attached.
  statement {
    sid = "LambdaRoleRead"
    actions = [
      "iam:GetRole", "iam:GetRolePolicy", "iam:ListRolePolicies", "iam:ListAttachedRolePolicies",
      "iam:ListInstanceProfilesForRole", "iam:ListRoleTags", "iam:DeleteRole",
      "iam:UpdateAssumeRolePolicy", "iam:TagRole", "iam:UntagRole",
    ]
    resources = [local.lambda_role_arn]
  }
  statement {
    sid = "LambdaRoleWriteWithBoundary"
    actions = [
      "iam:CreateRole", "iam:PutRolePolicy", "iam:DeleteRolePolicy",
      "iam:AttachRolePolicy", "iam:DetachRolePolicy", "iam:PutRolePermissionsBoundary",
    ]
    resources = [local.lambda_role_arn]
    condition {
      test     = "StringEquals"
      variable = "iam:PermissionsBoundary"
      values   = [local.boundary_arn]
    }
  }
  statement {
    sid       = "PassLambdaRoleToLambdaOnly"
    actions   = ["iam:PassRole"]
    resources = [local.lambda_role_arn]
    condition {
      test     = "StringEquals"
      variable = "iam:PassedToService"
      values   = ["lambda.amazonaws.com"]
    }
  }

  # API Gateway HTTP APIs (API Gateway has no name-scoped ARNs for HTTP APIs).
  statement {
    sid       = "ApiGateway"
    actions   = ["apigateway:GET", "apigateway:POST", "apigateway:PUT", "apigateway:PATCH", "apigateway:DELETE", "apigateway:TagResource", "apigateway:UntagResource"]
    resources = ["arn:aws:apigateway:${var.region}::/apis", "arn:aws:apigateway:${var.region}::/apis/*", "arn:aws:apigateway:${var.region}::/tags/*"]
  }

  # CloudWatch Logs: the project's log groups.
  statement {
    sid = "LogGroups"
    actions = [
      "logs:CreateLogGroup", "logs:DeleteLogGroup", "logs:PutRetentionPolicy", "logs:DeleteRetentionPolicy",
      "logs:TagResource", "logs:UntagResource", "logs:ListTagsForResource", "logs:TagLogGroup", "logs:ListTagsLogGroup",
      "logs:PutMetricFilter", "logs:DeleteMetricFilter",
    ]
    resources = [
      "arn:aws:logs:${var.region}:${local.account}:log-group:/aws/lambda/${var.project}-*",
      "arn:aws:logs:${var.region}:${local.account}:log-group:/aws/lambda/${var.project}-*:*",
      "arn:aws:logs:${var.region}:${local.account}:log-group:/aws/apigateway/${var.project}-*",
      "arn:aws:logs:${var.region}:${local.account}:log-group:/aws/apigateway/${var.project}-*:*",
    ]
  }
  # Describe calls and API Gateway access-log delivery do not support resource scoping.
  statement {
    sid = "LogsUnscopable"
    actions = [
      "logs:DescribeLogGroups", "logs:DescribeMetricFilters",
      "logs:CreateLogDelivery", "logs:GetLogDelivery", "logs:UpdateLogDelivery", "logs:DeleteLogDelivery",
      "logs:ListLogDeliveries", "logs:PutResourcePolicy", "logs:DescribeResourcePolicies",
    ]
    resources = ["*"]
  }
}
