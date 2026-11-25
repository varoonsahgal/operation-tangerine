###############################################################################
# CloudWatch "Mission Control" dashboard
###############################################################################

resource "aws_cloudwatch_dashboard" "mission_control" {
  dashboard_name = "${local.name}-mission-control"

  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric", x = 0, y = 0, width = 12, height = 6
        properties = {
          title  = "Zest agent - invocations & errors"
          region = var.region
          stat   = "Sum"
          period = 60
          view   = "timeSeries"
          metrics = [
            ["AWS/Lambda", "Invocations", "FunctionName", local.lambda_name],
            [".", "Errors", ".", "."],
            [".", "Throttles", ".", "."],
          ]
        }
      },
      {
        type = "metric", x = 12, y = 0, width = 12, height = 6
        properties = {
          title  = "Zest agent - duration (p50 / p90 / max)"
          region = var.region
          period = 60
          view   = "timeSeries"
          metrics = [
            ["AWS/Lambda", "Duration", "FunctionName", local.lambda_name, { stat = "p50" }],
            ["...", { stat = "p90" }],
            ["...", { stat = "Maximum" }],
          ]
        }
      },
      {
        type = "metric", x = 0, y = 6, width = 12, height = 6
        properties = {
          title  = "Aurora Serverless v2 - capacity"
          region = var.region
          period = 60
          stat   = "Average"
          view   = "timeSeries"
          metrics = [
            ["AWS/RDS", "ServerlessDatabaseCapacity", "DBClusterIdentifier", aws_rds_cluster.aurora.cluster_identifier],
            [".", "ACUUtilization", ".", "."],
          ]
        }
      },
      {
        type = "metric", x = 12, y = 6, width = 12, height = 6
        properties = {
          title  = "Agent memory (DynamoDB) - consumed capacity"
          region = var.region
          period = 60
          stat   = "Sum"
          view   = "timeSeries"
          metrics = [
            ["AWS/DynamoDB", "ConsumedReadCapacityUnits", "TableName", aws_dynamodb_table.memory.name],
            [".", "ConsumedWriteCapacityUnits", ".", "."],
          ]
        }
      },
      {
        type = "log", x = 0, y = 12, width = 24, height = 6
        properties = {
          title  = "Zest agent - recent actions"
          region = var.region
          view   = "table"
          query  = "SOURCE '/aws/lambda/${local.lambda_name}' | filter event = 'agent_action' | fields @timestamp, action, ok, duration_ms, error | sort @timestamp desc | limit 50"
        }
      },
    ]
  })
}
