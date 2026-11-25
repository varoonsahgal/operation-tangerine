###############################################################################
# Lambda - "Zest", the customer-intelligence agent
###############################################################################

data "archive_file" "agent" {
  type        = "zip"
  source_file = "${path.module}/lambda/agent.py"
  output_path = "${path.module}/build/agent.zip"
}

# ---- Anthropic SDK layer (for the `ask` action that calls Claude) ----

resource "terraform_data" "anthropic_layer_build" {
  count = var.enable_claude_agent ? 1 : 0

  triggers_replace = [
    filesha256("${path.module}/lambda/requirements.txt"),
    filesha256("${path.module}/scripts/build_layer.sh"),
  ]

  provisioner "local-exec" {
    command = "bash '${path.module}/scripts/build_layer.sh' '${path.module}/build/layer' '${path.module}/lambda/requirements.txt'"
  }
}

data "archive_file" "anthropic_layer" {
  count       = var.enable_claude_agent ? 1 : 0
  type        = "zip"
  source_dir  = "${path.module}/build/layer"
  output_path = "${path.module}/build/anthropic-layer.zip"

  depends_on = [terraform_data.anthropic_layer_build]
}

resource "aws_lambda_layer_version" "anthropic" {
  count               = var.enable_claude_agent ? 1 : 0
  layer_name          = "${local.name}-anthropic-sdk"
  filename            = data.archive_file.anthropic_layer[0].output_path
  source_code_hash    = data.archive_file.anthropic_layer[0].output_base64sha256
  compatible_runtimes = ["python3.13"]
  description         = "anthropic[bedrock] SDK for Claude in Amazon Bedrock"
}

# ---- function ----

resource "aws_cloudwatch_log_group" "agent" {
  name              = "/aws/lambda/${local.lambda_name}"
  retention_in_days = var.log_retention_days
}

resource "aws_lambda_function" "agent" {
  function_name = local.lambda_name
  description   = "Zest - Citrus & Co. customer-intelligence agent (Operation Tangerine)"
  role          = aws_iam_role.agent.arn
  runtime       = "python3.13"
  architectures = ["x86_64"]
  handler       = "agent.handler"
  timeout       = 120
  memory_size   = 512

  filename         = data.archive_file.agent.output_path
  source_code_hash = data.archive_file.agent.output_base64sha256
  layers           = var.enable_claude_agent ? [aws_lambda_layer_version.anthropic[0].arn] : []

  environment {
    variables = {
      DB_CLUSTER_ARN    = aws_rds_cluster.aurora.arn
      DB_SECRET_ARN     = aws_secretsmanager_secret.admin.arn
      DB_NAME           = var.db_name
      MEMORY_TABLE      = aws_dynamodb_table.memory.name
      MEMORY_TTL_DAYS   = tostring(var.memory_ttl_days)
      KB_ID             = local.kb_id
      EMBED_MODEL_ID    = var.embedding_model_id
      EMBED_DIMENSIONS  = tostring(var.embedding_dimensions)
      AGENT_MODEL_ID    = var.agent_model_id
      FALLBACK_MODEL_ID = var.fallback_model_id
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.agent,
    aws_iam_role_policy.agent_data,
    aws_iam_role_policy_attachment.agent_logs,
    aws_secretsmanager_secret_version.admin,
  ]
}
