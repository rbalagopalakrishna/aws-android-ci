resource "aws_cloudwatch_event_rule" "pull_request_event" {
  name        = "capture-pull-request-event"
  description = "Managed by Terraform. Capture all events related to pull-requests"
  is_enabled = true
  event_pattern = <<PATTERN
{
  "source": [
    "aws.codecommit"
  ],
  "resources": [
    "${var.repo_arn}"
  ],
  "detail-type": [
    "CodeCommit Pull Request State Change"
  ],
  "detail": {
    "event": ["pullRequestCreated"],
    "repositoryNames": ["${var.repo}"]
  }
}
PATTERN
}

#$.detail.notificationBody
resource "aws_cloudwatch_event_target" "sns" {
  rule       = "${aws_cloudwatch_event_rule.pull_request_event.name}"
  target_id  = "SendToSNS"
  arn        = "${var.lambda_function_arn}"
  input_path = "$.detail.notificationBody"
}
