output "api_endpoint" {
  description = "Base invoke URL for the HTTP API"
  value       = aws_apigatewayv2_stage.default.invoke_url
}

output "lambda_function_name" {
  description = "Name of the deployed Lambda function"
  value       = aws_lambda_function.url_shortener.function_name
}

output "dynamodb_table_name" {
  description = "Name of the DynamoDB table storing short codes"
  value       = aws_dynamodb_table.urls.name
}
