# ---------- SNS topic and email subscription ----------
resource "aws_sns_topic" "new_item" {
  name = "${var.project_name}-new-item"
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.new_item.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# ---------- Package the Lambda code ----------
data "archive_file" "lambda" {
  type        = "zip"
  source_file = "${path.module}/lambda/handler.py"
  output_path = "${path.module}/lambda/handler.zip"
}

# ---------- Lambda execution role ----------
data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda" {
  name               = "${var.project_name}-notify-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

data "aws_iam_policy_document" "lambda_permissions" {
  statement {
    sid = "ReadTheStream"
    actions = [
      "dynamodb:GetRecords",
      "dynamodb:GetShardIterator",
      "dynamodb:DescribeStream",
      "dynamodb:ListStreams",
    ]
    resources = [var.table_stream_arn]
  }

  statement {
    sid       = "PublishToOneTopic"
    actions   = ["sns:Publish"]
    resources = [aws_sns_topic.new_item.arn]
  }

  statement {
    sid = "WriteOwnLogs"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["arn:aws:logs:*:*:log-group:/aws/lambda/${var.project_name}-notify:*"]
  }
}

resource "aws_iam_role_policy" "lambda" {
  name   = "notify-permissions"
  role   = aws_iam_role.lambda.id
  policy = data.aws_iam_policy_document.lambda_permissions.json
}

# ---------- Log group with short retention (keeps cost at zero) ----------
resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${var.project_name}-notify"
  retention_in_days = 1
}

# ---------- The Lambda function ----------
resource "aws_lambda_function" "notify" {
  function_name    = "${var.project_name}-notify"
  role             = aws_iam_role.lambda.arn
  runtime          = "python3.12"
  handler          = "handler.lambda_handler"
  filename         = data.archive_file.lambda.output_path
  source_code_hash = data.archive_file.lambda.output_base64sha256
  timeout          = 10
  memory_size      = 128

  environment {
    variables = {
      TOPIC_ARN = aws_sns_topic.new_item.arn
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.lambda,
    aws_iam_role_policy.lambda,
  ]
}

# ---------- Connect the stream to the Lambda ----------
resource "aws_lambda_event_source_mapping" "stream" {
  event_source_arn  = var.table_stream_arn
  function_name     = aws_lambda_function.notify.arn
  starting_position = "LATEST"
  batch_size        = 10

  maximum_retry_attempts         = 3
  bisect_batch_on_function_error = true

  # Only invoke the function for INSERT events (saves invocations and cost)
  filter_criteria {
    filter {
      pattern = jsonencode({ eventName = ["INSERT"] })
    }
  }
}