# Observability: latency metric from the app's JSON logs, one error alarm, a small dashboard.
# The SNS topic and its email subscription live in the bootstrap stack.

locals {
  alerts_topic_arn = "arn:aws:sns:${var.region}:${local.account}:${var.project}-alerts"
  metric_namespace = "DocQA"
}

# --- Metric filter: every request log line has latency_ms -> custom metric DocQA/LatencyMs ---
resource "aws_cloudwatch_log_metric_filter" "latency" {
  name           = "${var.project}-latency"
  log_group_name = aws_cloudwatch_log_group.lambda.name
  pattern        = "{ $.latency_ms = * }"

  metric_transformation {
    name      = "LatencyMs"
    namespace = local.metric_namespace
    value     = "$.latency_ms"
    unit      = "Milliseconds"
  }
}

# --- One alarm: Lambda errors + API 5xx over 5 minutes ---
# The app turns unhandled exceptions into 500s, so Lambda "Errors" alone would miss most
# failures; adding API Gateway 5xx also catches timeouts and crashes before the app runs.
resource "aws_cloudwatch_metric_alarm" "errors" {
  alarm_name          = "${var.project}-errors"
  alarm_description   = "Lambda errors + API 5xx >= ${var.error_alarm_threshold} in 5 minutes"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = var.error_alarm_threshold
  evaluation_periods  = 1
  treat_missing_data  = "notBreaching"
  alarm_actions       = [local.alerts_topic_arn]
  ok_actions          = [local.alerts_topic_arn]

  metric_query {
    id          = "total"
    expression  = "FILL(lambda_errors, 0) + FILL(api_5xx, 0)"
    label       = "Lambda errors + API 5xx"
    return_data = true
  }

  metric_query {
    id = "lambda_errors"
    metric {
      namespace   = "AWS/Lambda"
      metric_name = "Errors"
      dimensions  = { FunctionName = aws_lambda_function.api.function_name }
      period      = 300
      stat        = "Sum"
    }
  }

  metric_query {
    id = "api_5xx"
    metric {
      namespace   = "AWS/ApiGateway"
      metric_name = "5xx"
      dimensions  = { ApiId = aws_apigatewayv2_api.http.id }
      period      = 300
      stat        = "Sum"
    }
  }
}

# --- Dashboard: errors and p95 latency ---
resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${var.project}-overview"
  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric", x = 0, y = 0, width = 12, height = 6
        properties = {
          title  = "Errors (5 min sums)"
          region = var.region
          stat   = "Sum"
          period = 300
          metrics = [
            ["AWS/Lambda", "Errors", "FunctionName", aws_lambda_function.api.function_name, { label = "Lambda errors" }],
            ["AWS/ApiGateway", "5xx", "ApiId", aws_apigatewayv2_api.http.id, { label = "API 5xx" }],
            ["AWS/ApiGateway", "4xx", "ApiId", aws_apigatewayv2_api.http.id, { label = "API 4xx" }],
          ]
        }
      },
      {
        type = "metric", x = 12, y = 0, width = 12, height = 6
        properties = {
          title  = "p95 latency (ms)"
          region = var.region
          stat   = "p95"
          period = 300
          metrics = [
            [local.metric_namespace, "LatencyMs", { label = "App p95 (from logs)" }],
            ["AWS/ApiGateway", "Latency", "ApiId", aws_apigatewayv2_api.http.id, { label = "API Gateway p95 (incl. cold starts)" }],
          ]
        }
      },
      {
        type = "metric", x = 0, y = 6, width = 24, height = 5
        properties = {
          title  = "Requests (5 min sums)"
          region = var.region
          stat   = "Sum"
          period = 300
          metrics = [
            ["AWS/ApiGateway", "Count", "ApiId", aws_apigatewayv2_api.http.id, { label = "API requests" }],
            ["AWS/Lambda", "Invocations", "FunctionName", aws_lambda_function.api.function_name, { label = "Lambda invocations" }],
          ]
        }
      },
    ]
  })
}
