# Illustrative only. CloudWatch Cross-Account Observability (OAM) is
# the native mechanism that gives the monitoring account a single-pane
# dashboard/alarms view over metrics that physically live in each
# spoke account -- without copying metric data anywhere. Run the sink
# side once in the monitoring account, and the link side once per
# spoke account (or centrally via AWS Organizations, which OAM
# supports natively for auto-enrollment of new accounts).

# --- In the monitoring (observer) account ---
resource "aws_oam_sink" "diskmon_sink" {
  name = "diskmon-central-sink"
}

resource "aws_oam_sink_policy" "diskmon_sink_policy" {
  sink_identifier = aws_oam_sink.diskmon_sink.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { AWS = "*" }
      Action    = ["oam:CreateLink", "oam:UpdateLink"]
      Resource  = "*"
      Condition = {
        StringEquals = { "aws:PrincipalOrgID" = "o-example12345" }
      }
    }]
  })
}

# --- In each spoke account (source) — repeat per account, or automate
#     via an AWS Organizations service-managed StackSet ---
resource "aws_oam_link" "diskmon_link" {
  sink_identifier  = "arn:aws:oam:ap-south-1:999999999999:sink/diskmon-central-sink"
  resource_types   = ["AWS::CloudWatch::Metric", "AWS::Logs::LogGroup"]
  label_template   = "$AccountName"
}
