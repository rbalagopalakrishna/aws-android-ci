resource "aws_iam_role" "codepipeline_role" {
  name = "codepipeline-ios-service-role"
  path  = "/service-role/"
  # Terraform's "jsonencode" function converts a
  # Terraform expression result to valid JSON syntax.
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Sid    = ""
        Principal = {
          Service = "codepipeline.amazonaws.com"
        }
      },
    ]
  })

}

#resource "aws_iam_policy" "codepipeline_policy" {
#  name        = "codepipeline-android-policy"
#  description = "policy for codepipeline-android-service-role"
#
#  policy = <<EOF
#{
#  "Version": "2012-10-17",
#  "Statement": [
#    {
#      "Action": [
#        "codecommit:*"
#      ],
#      "Effect": "Allow",
#      "Resource": "*"
#    },
#    {
#      "Action": [
#        "s3:*",
#        "s3-object-lambda:*"
#      ],
#      "Effect": "Allow",
#      "Resource": "*"
#    },
#    {
#      "Action": [
#        "codebuild:*"
#      ],
#      "Effect": "Allow",
#      "Resource": "*"
#    }
#  ]
#}
#EOF
#}

resource "aws_iam_role_policy_attachment" "test-attach" {
  role       = aws_iam_role.codepipeline_role.name
  #policy_arn = aws_iam_policy.codepipeline_policy.arn
  policy_arn = ""
}
