resource "aws_s3_bucket" "bucket" {
  bucket = "dt-android"
}

resource "aws_s3_bucket_acl" "aws_bucket_acl" {
  bucket = aws_s3_bucket.bucket.id
  acl    = "private"
}

resource "aws_iam_role" "role" {
  name = "codebuild-android-service-role"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "codebuild.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
}

resource "aws_iam_role_policy" "policy" {
  role = "${aws_iam_role.role.name}"

  policy = <<POLICY
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Resource": [
        "*"
      ],
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:*"
      ],
      "Resource": [
        "${aws_s3_bucket.bucket.arn}",
        "${aws_s3_bucket.bucket.arn}/*"
      ]
    }
  ]
}
POLICY
}

resource "aws_codebuild_project" "codebuild_project" {
  name          = "android-dev"
  description   = "android_codebuild_project"
  concurrent_build_limit = "5"
  build_timeout = "10"
  service_role  = "${aws_iam_role.role.arn}"

  artifacts {
    type = "NO_ARTIFACTS"
  }

  cache {
    type     = "S3"
    location = "${aws_s3_bucket.bucket.bucket}"
  }

  environment {
    compute_type                = "BUILD_GENERAL1_SMALL"
    image                       = "aws/codebuild/amazonlinux2-x86_64-standard:3.0"
    type                        = "LINUX_CONTAINER"
    image_pull_credentials_type = "CODEBUILD"
    privileged_mode             = "false"

  }

  source {
    type            = "CODECOMMIT"
    location        = "https://git-codecommit.ap-south-1.amazonaws.com/v1/repos/Dev-Dt-Android"
    buildspec       = "buildspec/build_gradlew.yaml"
    git_clone_depth = 1
  }
  source_version = "develop"
}


resource "aws_codebuild_project" "codebuild_project_master" {
  name          = "android-master"
  description   = "android_codebuild_project_master"
  concurrent_build_limit = "5"
  build_timeout = "10"
  service_role  = "${aws_iam_role.role.arn}"

  artifacts {
    type = "NO_ARTIFACTS"
  }

  cache {
    type     = "S3"
    location = "${aws_s3_bucket.bucket.bucket}"
  }

  environment {
    compute_type                = "BUILD_GENERAL1_SMALL"
    image                       = "aws/codebuild/amazonlinux2-x86_64-standard:3.0"
    type                        = "LINUX_CONTAINER"
    image_pull_credentials_type = "CODEBUILD"
    privileged_mode             = "false"

  }

  source {
    type            = "CODECOMMIT"
    location        = "https://git-codecommit.ap-south-1.amazonaws.com/v1/repos/Dev-Dt-Android"
    buildspec       = "buildspec/build_gradlew.yaml"
    git_clone_depth = 1
  }
  source_version = "master"
}
