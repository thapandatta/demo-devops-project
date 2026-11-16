resource "aws_dynamodb_table" "items" {
  name         = "${var.project_name}-items"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }

  point_in_time_recovery {
    enabled = false # keep costs at zero for learning
  }

  server_side_encryption {
    enabled = true
  }
}

# ---------- Let the EC2 instance use ONLY this table ----------
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