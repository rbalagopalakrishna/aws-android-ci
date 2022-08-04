resource "aws_s3_bucket" "bucket" {
  bucket = "android-source"
}

resource "aws_s3_bucket" "android_apk_build_bucket" {
  bucket = "android-builds"
}

resource "aws_s3_bucket" "android_apk_release_bucket" {
  bucket = "android-release"
}

resource "aws_s3_bucket_acl" "aws_bucket_acl" {
  bucket = aws_s3_bucket.bucket.id
  acl    = "private"
}

resource "aws_s3_bucket_acl" "aws_android_apk_build_bucket_acl" {
  bucket = aws_s3_bucket.android_apk_build_bucket.id
  acl    = "private"
}

resource "aws_s3_bucket_acl" "aws_android_apk_release_bucket_acl" {
  bucket = aws_s3_bucket.android_apk_release_bucket.id
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

#resource "aws_iam_role_policy" "policy" {
#  role = "${aws_iam_role.role.name}"
#
#  policy = <<POLICY
#{
#  "Version": "2012-10-17",
#  "Statement": [
#    {
#      "Effect": "Allow",
#      "Resource": [
#        "*"
#      ],
#      "Action": [
#        "logs:CreateLogGroup",
#        "logs:CreateLogStream",
#        "logs:PutLogEvents"
#      ]
#    },
#    {
#      "Effect": "Allow",
#      "Action": [
#        "s3:*"
#      ],
#      "Resource": [
#        "${aws_s3_bucket.bucket.arn}",
#        "${aws_s3_bucket.bucket.arn}/*"
#      ]
#    }
#  ]
#}
#POLICY
#}

resource "aws_iam_role_policy_attachment" "test-attach" {
  role       = aws_iam_role.role.name
  #policy_arn = aws_iam_policy.codepipeline_policy.arn
  policy_arn = "arn:aws:iam::323144884758:policy/Accenture_Devops_policy"
}

resource "aws_codebuild_project" "codebuild_project" {
  name          = "android-develop-apk-build"
  description   = "android_codebuild_project"
  concurrent_build_limit = "5"
  build_timeout = "10"
  service_role  = "${aws_iam_role.role.arn}"

  artifacts {
    type = "NO_ARTIFACTS"
  }

#  artifacts {
#    type = "S3"
#    name = "Dev-Dt-Android"
#    path = "app/build/outputs/apk/debug/app-debug.apk"
#    namespace_type = "BUILD_ID"
#    location = "android-application"
#    packaging = "ZIP"
#  }

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
    location        = ""
    buildspec       = "buildspec/build_gradlew.yaml"
    git_clone_depth = 1
  }
  source_version = "develop"
}


resource "aws_codebuild_project" "codebuild_project_master" {
  name          = "android-master-apk-build"
  description   = "android_codebuild_project_master"
  concurrent_build_limit = 5
  build_timeout = 30
  service_role  = "${aws_iam_role.role.arn}"
  queued_timeout = 30

  artifacts {
    type = "NO_ARTIFACTS"
  }

#  artifacts {
#    bucket_owner_access = "FULL"
#    type = "S3"
#    name = "Dev-Dt-Android"
#    path = "app/build/outputs/apk/debug/app-debug.apk"
#    namespace_type = "BUILD_ID"
#    location = "android-application"
#    packaging = "ZIP"
#  }

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
    location        = ""
    buildspec       = "buildspec/build_gradlew.yaml"
    git_clone_depth = 1
  }
  source_version = "master"
}
