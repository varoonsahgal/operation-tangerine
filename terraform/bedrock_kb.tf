###############################################################################
# Bedrock Knowledge Base on Aurora PostgreSQL (OPTIONAL - off by default)
#
# On the exam you build this by hand, so Lab 2.6 does it in the console.
# Set create_knowledge_base = true only AFTER `labctl db-setup kb` has created
# the bedrock_integration.bedrock_kb table: Bedrock validates the table at
# creation time and fails if it is missing or has the wrong shape.
###############################################################################

locals {
  kb_id = var.create_knowledge_base ? aws_bedrockagent_knowledge_base.kb[0].id : var.knowledge_base_id
}

resource "aws_bedrockagent_knowledge_base" "kb" {
  count    = var.create_knowledge_base ? 1 : 0
  name     = "${local.name}-product-kb"
  role_arn = aws_iam_role.kb.arn

  knowledge_base_configuration {
    type = "VECTOR"
    vector_knowledge_base_configuration {
      embedding_model_arn = local.embedding_model_arn
    }
  }

  storage_configuration {
    type = "RDS"
    rds_configuration {
      resource_arn           = aws_rds_cluster.aurora.arn
      credentials_secret_arn = aws_secretsmanager_secret.kb_user.arn
      database_name          = var.db_name
      table_name             = "bedrock_integration.bedrock_kb"

      field_mapping {
        primary_key_field     = "id"
        vector_field          = "embedding"
        text_field            = "chunks"
        metadata_field        = "metadata"
        custom_metadata_field = "custom_metadata" # enables metadata filtering (Lab 2.7)
      }
    }
  }

  depends_on = [aws_iam_role_policy.kb_access, aws_rds_cluster_instance.writer]
}

resource "aws_bedrockagent_data_source" "docs" {
  count             = var.create_knowledge_base ? 1 : 0
  knowledge_base_id = aws_bedrockagent_knowledge_base.kb[0].id
  name              = "citrus-docs"

  data_source_configuration {
    type = "S3"
    s3_configuration {
      bucket_arn         = aws_s3_bucket.docs.arn
      inclusion_prefixes = ["docs/"]
    }
  }

  vector_ingestion_configuration {
    chunking_configuration {
      chunking_strategy = "FIXED_SIZE"
      fixed_size_chunking_configuration {
        max_tokens         = 300
        overlap_percentage = 20
      }
    }
  }
}
