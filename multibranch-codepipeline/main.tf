terraform {
  required_version = "~> 1.0"
}

provider "aws" {
  region = "${var.aws_region}"
}

data "aws_caller_identity" "current" {}

module "lambda" {
  source                            = "./modules/lambda"
  lambda_function_name              = "Android-Pipeline-Events"
}

module "sns" {
  source                        = "./modules/sns"
  repo                          = "${var.git_repository_name}"
  account_number                = "${data.aws_caller_identity.current.account_id}"
  lambda_function_name 		= "Android-Pipeline-Events"
  lambda_function_arn  		= "${module.lambda.lambda_function_arn}"
}

module "codepipeline" {
  source                       = "./modules/codepipeline"
}

module "codebuild" {
  source                       = "./modules/codebuild"
}
