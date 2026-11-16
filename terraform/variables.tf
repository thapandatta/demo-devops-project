variable "region" {
  type    = string
  default = "us-east-1"
}

variable "project_name" {
  type    = string
  default = "hello-user"
}

variable "instance_type" {
  type    = string
  default = "t3.micro"
}

variable "github_repo" {
  description = "GitHub repo in the form owner/repo"
  type        = string
}

variable "alert_email" {
  description = "Email for budget alerts"
  type        = string
}