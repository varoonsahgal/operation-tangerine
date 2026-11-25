variable "region" {
  description = "AWS region for every lab resource. Pick one where Bedrock, Titan Text Embeddings V2 and Claude in Amazon Bedrock are all available (us-east-1 and us-west-2 are safe bets)."
  type        = string
  default     = "us-east-1"
}

variable "prefix" {
  description = "Name prefix for every resource."
  type        = string
  default     = "tangerine"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,14}$", var.prefix))
    error_message = "prefix must be 2-15 chars: lowercase letters, digits, hyphens, starting with a letter."
  }
}

variable "student_id" {
  description = "Short unique id so several students can share one AWS account (e.g. your initials)."
  type        = string
  default     = "student1"

  validation {
    condition     = can(regex("^[a-z0-9]{2,12}$", var.student_id))
    error_message = "student_id must be 2-12 lowercase letters or digits."
  }
}

# ---------------- Aurora ----------------

variable "aurora_pg_major" {
  description = "Aurora PostgreSQL major version. The latest minor version of this major is selected automatically."
  type        = string
  default     = "16"
}

variable "aurora_min_acu" {
  description = "Serverless v2 minimum ACUs. 0.5 keeps the cluster warm during class. 0 enables auto-pause (cheaper, but the first query after a pause waits ~15s)."
  type        = number
  default     = 0.5
}

variable "aurora_max_acu" {
  description = "Serverless v2 maximum ACUs."
  type        = number
  default     = 4
}

variable "db_name" {
  description = "Database the agent uses."
  type        = string
  default     = "agentdb"
}

# ---------------- Bedrock ----------------

variable "embedding_model_id" {
  description = "Embedding model used by the Knowledge Base and the pgvector labs."
  type        = string
  default     = "amazon.titan-embed-text-v2:0"
}

variable "embedding_dimensions" {
  description = "Vector dimensions produced by the embedding model. Titan Text Embeddings V2 defaults to 1024."
  type        = number
  default     = 1024
}

variable "create_knowledge_base" {
  description = "false (default): you build the Knowledge Base by hand in the console during Lab 2.6, like on the exam. true: Terraform builds it for you (only after the vector table exists - see setup guide)."
  type        = bool
  default     = false
}

variable "knowledge_base_id" {
  description = "ID of a Knowledge Base you created in the console. Terraform wires it into the Lambda's KB_ID environment variable."
  type        = string
  default     = ""
}

variable "enable_claude_agent" {
  description = "Build the Anthropic SDK Lambda layer so the agent's `ask` action can call Claude in Amazon Bedrock. Requires python3 + pip on the machine running terraform."
  type        = bool
  default     = true
}

variable "agent_model_id" {
  description = "Claude model for the agent's reasoning loop (Claude in Amazon Bedrock / bedrock-mantle model ID)."
  type        = string
  default     = "anthropic.claude-opus-5-5"
}

variable "fallback_model_id" {
  description = "Model the SDK retries on if the main model declines a request. Leave empty to disable."
  type        = string
  default     = "anthropic.claude-opus-4-8"
}

variable "memory_ttl_days" {
  description = "How long agent conversation memory lives before DynamoDB TTL expires it."
  type        = number
  default     = 7
}

variable "log_retention_days" {
  description = "CloudWatch Logs retention for the agent Lambda."
  type        = number
  default     = 14
}
