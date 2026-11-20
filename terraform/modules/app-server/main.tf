# ---------- IAM role for the instance ----------
data "aws_iam_policy_document" "ec2_assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ec2_ssm" {
  name               = "${var.project_name}-ec2-ssm-role"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume.json
}

resource "aws_iam_role_policy_attachment" "ssm_core" {
  role       = aws_iam_role.ec2_ssm.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "ec2_ssm" {
  name = "${var.project_name}-ec2-profile"
  role = aws_iam_role.ec2_ssm.name
}

# ---------- Security group: HTTP only, no SSH ----------
resource "aws_security_group" "web" {
  name        = "${var.project_name}-sg"
  description = "Allow HTTP inbound only"

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "All outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# ---------- EC2 instance ----------
resource "aws_instance" "web" {
  ami                         = "ami-096ef200a877f36af"
  instance_type               = var.instance_type
  iam_instance_profile        = aws_iam_instance_profile.ec2_ssm.name
  vpc_security_group_ids      = [aws_security_group.web.id]
  associate_public_ip_address = true

  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
  }

  root_block_device {
    volume_size = 8
    volume_type = "gp3"
    encrypted   = true
  }

  user_data = <<-USERDATA
    #!/bin/bash
    dnf install -y docker
    systemctl enable --now docker
    mkdir -p /usr/local/lib/docker/cli-plugins
    curl -SL https://github.com/docker/compose/releases/download/v2.29.7/docker-compose-linux-x86_64 \
      -o /usr/local/lib/docker/cli-plugins/docker-compose
    chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
    mkdir -p /opt/app
  USERDATA

  user_data_replace_on_change = true

  tags = {
    Name = "${var.project_name}-server"
  }
}

# ---------- DynamoDB table ----------
resource "aws_dynamodb_table" "items" {
  name         = "${var.project_name}-items"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  stream_enabled=true
  stream_view_type="NEW_IMAGE"

  attribute {
    name = "id"
    type = "S"
  }

  point_in_time_recovery {
    enabled = false
  }

  server_side_encryption {
    enabled = true
  }
}

# ---------- Let the instance use ONLY this table ----------
data "aws_iam_policy_document" "app_dynamodb" {
  statement {
    sid = "ItemsTableAccess"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:Scan",
      "dynamodb:DeleteItem",
      "dynamodb:UpdateItem",
      "dynamodb:DescribeTable",
    ]
    resources = [aws_dynamodb_table.items.arn]
  }
}

resource "aws_iam_role_policy" "app_dynamodb" {
  name   = "dynamodb-items-access"
  role   = aws_iam_role.ec2_ssm.id
  policy = data.aws_iam_policy_document.app_dynamodb.json
}