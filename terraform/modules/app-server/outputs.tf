output "public_ip" {
  value = aws_instance.web.public_ip
}

output "instance_id" {
  value = aws_instance.web.id
}

output "table_name" {
  value = aws_dynamodb_table.items.name
}