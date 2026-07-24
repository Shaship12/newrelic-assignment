data "archive_file" "lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/../app/lambda_function.py"
  output_path = "${path.module}/build/lambda_function.zip"
}

resource "aws_lambda_function" "url_shortener" {
  function_name    = "${var.app_name}-${var.environment}"
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  handler = "lambda_function.handler"
  runtime = "python3.12"
  role    = aws_iam_role.lambda_exec.arn

  memory_size = var.lambda_memory_size
  timeout     = var.lambda_timeout

  environment {
    variables = {
      TABLE_NAME = aws_dynamodb_table.urls.name
    }
  }

  # Log group is created explicitly below (with our own retention) rather
  # than letting Lambda auto-create one, so retention isn't "never expire".
  depends_on = [aws_cloudwatch_log_group.lambda_logs]
}

resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${var.app_name}-${var.environment}"
  retention_in_days = var.log_retention_days
}
