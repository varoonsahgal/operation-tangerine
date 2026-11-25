###############################################################################
# IAM - the Lambda execution role and the Knowledge Base service role
#
# Statement Sids matter: labctl's break-fix drills remove/alter specific Sids,
# and the grader checks them with the IAM policy simulator.
###############################################################################

# ---------------- Lambda execution role ----------------

data "aws_iam_policy_document" "lambda_trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "agent" {
  name               = "${local.name}-zest-agent-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_trust.json
}

resource "aws_iam_role_policy_attachment" "agent_logs" {
  role       = aws_iam_role.agent.name
  policy_arn = "arn:${local.partition}:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

data "aws_iam_policy_document" "agent_data" {
  statement {
    sid = "AuroraDataApi"
    actions = [
      "rds-data:ExecuteStatement",
      "rds-data:BatchExecuteStatement",
      "rds-data:BeginTransaction",
      "rds-data:CommitTransaction",
      "rds-data:RollbackTransaction",
    ]
    resources = [aws_rds_cluster.aurora.arn]
  }

  # The Data API reads the DB secret *with the caller's permissions*.
  statement {
    sid       = "AuroraSecret"
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [aws_secretsmanager_secret.admin.arn]
  }

  statement {
    sid = "AgentMemory"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
      "dynamodb:DeleteItem",
      "dynamodb:Query",
      "dynamodb:BatchWriteItem",
    ]
    resources = [
      aws_dynamodb_table.memory.arn,
      "${aws_dynamodb_table.memory.arn}/index/*",
    ]
  }

  statement {
    sid       = "KnowledgeBaseRetrieve"
    actions   = ["bedrock:Retrieve"]
    resources = [local.kb_arn_pattern]
  }

  statement {
    sid       = "Embeddings"
    actions   = ["bedrock:InvokeModel"]
    resources = [local.embedding_model_arn]
  }

  # Claude in Amazon Bedrock (the bedrock-mantle Messages API endpoint).
  statement {
    sid       = "ClaudeInBedrock"
    actions   = ["bedrock-mantle:CreateInference"]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "agent_data" {
  name   = "agent-data-access"
  role   = aws_iam_role.agent.id
  policy = data.aws_iam_policy_document.agent_data.json
}

# ---------------- Bedrock Knowledge Base service role ----------------

data "aws_iam_policy_document" "kb_trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["bedrock.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [local.account_id]
    }
    condition {
      test     = "ArnLike"
      variable = "aws:SourceArn"
      values   = [local.kb_arn_pattern]
    }
  }
}

resource "aws_iam_role" "kb" {
  name               = "${local.name}-kb-service-role"
  assume_role_policy = data.aws_iam_policy_document.kb_trust.json
}

data "aws_iam_policy_document" "kb_access" {
  statement {
    sid       = "EmbeddingModel"
    actions   = ["bedrock:InvokeModel"]
    resources = [local.embedding_model_arn]
  }

  statement {
    sid       = "AuroraDescribe"
    actions   = ["rds:DescribeDBClusters"]
    resources = [aws_rds_cluster.aurora.arn]
  }

  statement {
    sid       = "AuroraDataApi"
    actions   = ["rds-data:ExecuteStatement", "rds-data:BatchExecuteStatement"]
    resources = [aws_rds_cluster.aurora.arn]
  }

  statement {
    sid       = "KbSecret"
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [aws_secretsmanager_secret.kb_user.arn]
  }

  statement {
    sid       = "DocsList"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.docs.arn]
  }

  statement {
    sid       = "DocsRead"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.docs.arn}/*"]
  }
}

resource "aws_iam_role_policy" "kb_access" {
  name   = "kb-access"
  role   = aws_iam_role.kb.id
  policy = data.aws_iam_policy_document.kb_access.json
}
