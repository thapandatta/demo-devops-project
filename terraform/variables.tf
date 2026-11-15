variable "region" {
  type    = string
  default = "us-east-1"
}

# Use t2.micro or t3.micro depending on which is free-tier eligible in your account
variable "instance_type" {
  type    = string
  default = "t3.micro"
}

variable "project_name" {
  type    = string
  default = "hello-user"
}

variable "github_repo" {
  description = "GitHub repo in the form owner/repo"
  type        = string
}

variable "alert_email" {
  description = "Email for budget alerts"
  type        = string
}
