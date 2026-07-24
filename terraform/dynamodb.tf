resource "aws_dynamodb_table" "urls" {
  name         = "${var.app_name}-${var.environment}-urls"
  billing_mode = var.dynamodb_billing_mode
  hash_key     = "short_code"

  attribute {
    name = "short_code"
    type = "S"
  }

  # Point-in-time recovery only in prod - it costs more and dev/staging
  # data is disposable, so it's not worth paying for there.
  point_in_time_recovery {
    enabled = var.environment == "prod"
  }
}
