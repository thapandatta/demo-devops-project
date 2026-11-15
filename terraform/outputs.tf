output "public_ip" {
  value = aws_instance.web.public_ip
}

output "instance_id" {
  value = aws_instance.web.id
}

output "github_actions_role_arn" {
  description = "Put this in the AWS_ROLE_ARN GitHub secret"
  value       = aws_iam_role.github_actions.arn
}
