data "aws_codecommit_repository" "main_repo" {
  repository_name = "${var.repo}"
}

resource "aws_sns_topic" "notifier" {
  name = "codestart_notification_trigger"
}

resource "aws_sns_topic_policy" "default" {
  arn = "${aws_sns_topic.notifier.arn}"
  policy = "${data.aws_iam_policy_document.sns-topic-policy.json}"
}

resource "aws_sns_topic_subscription" "events_notifier" {
  topic_arn = "${aws_sns_topic.notifier.arn}"
  protocol  = "lambda"
  endpoint  = "${var.lambda_function_arn}"
}

data "aws_iam_policy_document" "sns-topic-policy" {
  version =  "2008-10-17"

  statement {
    sid = "CodeNotification_publish"
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["codestar-notifications.amazonaws.com"]
    }
    actions = ["SNS:Publish",]
    resources = ["${aws_sns_topic.notifier.arn}",]
  }
}

resource "aws_lambda_permission" "allow_event" {
  statement_id  = "AllowExecutionFromSNS"
  action        = "lambda:InvokeFunction"
  function_name = "${var.lambda_function_name}"
  principal     = "sns.amazonaws.com"
  source_arn    = "${aws_sns_topic.notifier.arn}"
}

resource "aws_codestarnotifications_notification_rule" "notification_rule" {
  detail_type    = "BASIC"
  event_type_ids = [
	"codecommit-repository-branches-and-tags-created",
	"codecommit-repository-branches-and-tags-updated",
        "codecommit-repository-pull-request-created",
        "codecommit-repository-pull-request-merged",
	"codecommit-repository-pull-request-source-updated"
        ]

  name     = "pull-requests"
  resource = "${data.aws_codecommit_repository.main_repo.arn}"

  target {
    address = "${aws_sns_topic.notifier.arn}"
  }
}
