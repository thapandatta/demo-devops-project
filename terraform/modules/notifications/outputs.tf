output "topic_arn" {
  value = aws_sns_topic.new_item.arn
}

output "lambda_name" {
  value = aws_lambda_function.notify.function_name
}