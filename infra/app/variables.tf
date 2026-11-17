variable "project" {
  type    = string
  default = "docqa"
}

variable "region" {
  type    = string
  default = "ap-southeast-1"
}

variable "lambda_zip_path" {
  description = "Built by scripts/build_lambda.py"
  type        = string
  default     = "../../build/lambda.zip"
}

variable "log_retention_days" {
  type    = number
  default = 14
}

variable "throttle_burst" {
  type    = number
  default = 20
}

variable "throttle_rate" {
  description = "Steady-state requests per second across the API."
  type        = number
  default     = 10
}

variable "enable_bedrock" {
  description = "Grant the Lambda bedrock:InvokeModel on one model and allow use_llm=true. Off by default (costs money)."
  type        = bool
  default     = false
}

variable "bedrock_model_id" {
  description = "Bedrock model ID, required when enable_bedrock = true."
  type        = string
  default     = ""
  validation {
    condition     = !var.enable_bedrock || length(var.bedrock_model_id) > 0
    error_message = "Set bedrock_model_id when enable_bedrock = true."
  }
}

variable "error_alarm_threshold" {
  description = "Alarm when Lambda errors + API 5xx in a 5-minute window reach this count."
  type        = number
  default     = 1
}
