# Permissions boundary that every role CI creates must carry. Even if the deploy role
# wrote an over-broad policy onto the Lambda execution role, the effective permissions
# could never exceed this: write own logs, and (optionally) invoke Bedrock models.

data "aws_iam_policy_document" "lambda_boundary" {
  statement {
    sid       = "OwnLogsOnly"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["arn:aws:logs:${var.region}:${local.account}:log-group:/aws/lambda/${var.project}-*:*"]
  }
  statement {
    sid       = "BedrockInvokeCeiling"
    actions   = ["bedrock:InvokeModel"]
    resources = ["arn:aws:bedrock:${var.region}::foundation-model/*"]
  }
}

resource "aws_iam_policy" "lambda_boundary" {
  name   = "${var.project}-lambda-boundary"
  policy = data.aws_iam_policy_document.lambda_boundary.json
}
