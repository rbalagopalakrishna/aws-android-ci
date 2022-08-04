output "lambda_function_arn" {
  value = "${resource.aws_lambda_function.events.arn}"
}
