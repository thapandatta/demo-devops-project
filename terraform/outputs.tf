output "public_ip" {
  value = module.app_server.public_ip
}

output "instance_id" {
  value = module.app_server.instance_id
}

output "dynamodb_table_name" {
  value = module.app_server.table_name
}

output "github_actions_role_arn" {
  description = "Put this in the AWS_ROLE_ARN GitHub secret"
  value       = module.cicd_access.role_arn
}