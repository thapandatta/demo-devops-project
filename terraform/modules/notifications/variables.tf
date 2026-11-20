variable "project_name" {
  type = string
}

variable "alert_email" {
  description = "Email address that receives new-item notifications"
  type        = string
}

variable "table_stream_arn" {
  description = "ARN of the DynamoDB stream to listen to"
  type        = string
}