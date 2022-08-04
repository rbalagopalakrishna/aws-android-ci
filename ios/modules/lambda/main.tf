resource "aws_iam_role" "iam_for_ios_lambda_events" {
  name = "lambda-ios-service-role"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF
}

resource "aws_cloudwatch_log_group" "cloudwatch_log_group_events" {
  name              = "/aws/lambda/${var.lambda_function_name}"
  retention_in_days = 0
}

resource "aws_iam_policy" "lambda_logging" {
  name        = "ios_lambda_logging"
  path        = "/"
  description = "IAM policy for logging from a lambda"

  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*",
      "Effect": "Allow"
    },
    {
      "Action": [
        "codecommit:*"
      ],
      "Effect": "Allow",
      "Resource": "*"
    },
    {
      "Action": [
        "codepipeline:*"
      ],
      "Effect": "Allow",
      "Resource": "*"
    },
    {
        "Action": [
            "iam:PassRole"
        ],
        "Effect": "Allow",
        "Resource": "*",
        "Condition": {
            "StringEquals": {
                "iam:PassedToService": [
                    "codepipeline.amazonaws.com"
                ]
            }
        }
    }
  ]
}
EOF
}

resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.iam_for_ios_lambda_events.name
  policy_arn = aws_iam_policy.lambda_logging.arn
  #policy_arn = "arn:aws:iam::323144884758:policy/Accenture_Devops_policy"
}

resource "aws_lambda_function" "events" {
  # If the file is not in the current working directory you will need to include a
  # path.module in the filename.
  filename      = "lambda_function_payload.zip"
  function_name = "${var.lambda_function_name}"
  role          = aws_iam_role.iam_for_ios_lambda_events.arn
  handler       = "lambda_function.lambda_handler"
  # The filebase64sha256() function is available in Terraform 0.11.12 and later
  # For Terraform 0.11.11 and earlier, use the base64sha256() function and the file() function:
  # source_code_hash = "${base64sha256(file("lambda_function_payload.zip"))}"
  source_code_hash = filebase64sha256("lambda_function_payload.zip")

  runtime = "python3.9"

  ephemeral_storage {
    size = 512 # Min 512 MB and the Max 10240 MB
  }

  timeout = 900

  environment {
    variables = {
      foo = "bar"
    }
  }
}
