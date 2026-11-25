output "lab" {
  description = "Everything labctl and the lab guides need. Run: terraform output lab"
  value = {
    region               = var.region
    account_id           = local.account_id
    name                 = local.name
    cluster_arn          = aws_rds_cluster.aurora.arn
    cluster_id           = aws_rds_cluster.aurora.cluster_identifier
    writer_instance_id   = aws_rds_cluster_instance.writer.identifier
    writer_instance_arn  = aws_rds_cluster_instance.writer.arn
    db_name              = var.db_name
    admin_secret_arn     = aws_secretsmanager_secret.admin.arn
    kb_user_secret_arn   = aws_secretsmanager_secret.kb_user.arn
    memory_table         = aws_dynamodb_table.memory.name
    memory_table_arn     = aws_dynamodb_table.memory.arn
    lambda_name          = aws_lambda_function.agent.function_name
    lambda_role_name     = aws_iam_role.agent.name
    lambda_role_arn      = aws_iam_role.agent.arn
    lambda_policy_name   = aws_iam_role_policy.agent_data.name
    kb_role_name         = aws_iam_role.kb.name
    kb_role_arn          = aws_iam_role.kb.arn
    kb_policy_name       = aws_iam_role_policy.kb_access.name
    docs_bucket          = aws_s3_bucket.docs.bucket
    docs_bucket_arn      = aws_s3_bucket.docs.arn
    knowledge_base_id    = local.kb_id
    data_source_id       = var.create_knowledge_base ? aws_bedrockagent_data_source.docs[0].data_source_id : ""
    embedding_model_id   = var.embedding_model_id
    embedding_model_arn  = local.embedding_model_arn
    embedding_dimensions = var.embedding_dimensions
    agent_model_id       = var.agent_model_id
    dashboard            = aws_cloudwatch_dashboard.mission_control.dashboard_name
    log_group            = aws_cloudwatch_log_group.agent.name
  }
}

output "next_steps" {
  value = <<-EOT

    🍊 Operation Tangerine base is deployed.

      1. Seed the database:        python3 ../labctl/labctl.py db-setup
      2. Check the agent's health: python3 ../labctl/labctl.py invoke health
      3. Open Mission Control:     https://${var.region}.console.aws.amazon.com/cloudwatch/home?region=${var.region}#dashboards/dashboard/${aws_cloudwatch_dashboard.mission_control.dashboard_name}

  EOT
}
