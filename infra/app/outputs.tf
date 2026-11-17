output "api_url" {
  value = aws_apigatewayv2_stage.default.invoke_url
}

output "function_name" {
  value = aws_lambda_function.api.function_name
}

output "lambda_log_group" {
  value = aws_cloudwatch_log_group.lambda.name
}
