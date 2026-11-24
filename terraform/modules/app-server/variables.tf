variable "project_name" {
  type = string
}

variable "instance_type" {
  type    = string
  default = "t3.micro"
}

variable "vpc_id" {
  description = "VPC the security group belongs to"
  type        = string
}

variable "subnet_id" {
  description = "Subnet the server launches into (a public subnet)"
  type        = string
}

