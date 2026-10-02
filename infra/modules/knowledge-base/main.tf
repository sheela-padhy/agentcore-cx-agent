data "aws_region" "current" {}

resource "aws_iam_role_policy" "bedrock_kb_sample_kb_model" {
  name = "AmazonBedrockS3VectorsPolicyForKnowledgeBase_${var.kb_name}"
  role = var.bedrock_role_name
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action   = ["s3vectors:*"]
        Effect   = "Allow"
        Resource = [var.s3_vector_bucket_arn, var.s3_vector_index_arn]
      },
      {
        Action = ["bedrock:InvokeModel"]
        Effect = "Allow"
        Resource = [
          "arn:aws:bedrock:${data.aws_region.current.name}::foundation-model/amazon.titan-embed-*"
        ]
      },
      {
        Action   = ["s3:ListBucket", "s3:GetObject"]
        Effect   = "Allow"
        Resource = [var.s3_arn, "${var.s3_arn}/*"]
      }
    ]
  })
}

resource "time_sleep" "iam_consistency_delay" {
  create_duration = "240s"
  depends_on      = [aws_iam_role_policy.bedrock_kb_sample_kb_model]
}


resource "aws_bedrockagent_knowledge_base" "sample_kb" {
  name     = var.kb_name
  role_arn = var.bedrock_role_arn
  knowledge_base_configuration {
    vector_knowledge_base_configuration {
      embedding_model_arn = "arn:aws:bedrock:${data.aws_region.current.name}::foundation-model/amazon.titan-embed-text-v2:0"
    }
    type = "VECTOR"
  }
  storage_configuration {
    type = "S3_VECTORS"
    s3_vectors_configuration {
      # index_arn alone fully identifies the bucket too - AWS rejects
      # specifying both vector_bucket_arn and index_arn together
      # ("cannot be specified when index_arn is specified").
      index_arn = var.s3_vector_index_arn
    }
  }
  depends_on = [time_sleep.iam_consistency_delay, aws_iam_role_policy.bedrock_kb_sample_kb_model]
}

resource "aws_bedrockagent_data_source" "sample_kb" {
  knowledge_base_id = aws_bedrockagent_knowledge_base.sample_kb.id
  name              = "${var.kb_name}DataSource"
  # RETAIN (not the AWS default DELETE): deleting the KB should not also
  # try to delete vector data from the underlying store first - that step
  # can fail if the store is also being destroyed in the same apply
  # (exactly what happened migrating from OpenSearch to S3 Vectors: the
  # access policy got destroyed before the KB finished its own internal
  # vector-store cleanup, leaving the KB stuck in DELETE_UNSUCCESSFUL).
  data_deletion_policy = "RETAIN"
  data_source_configuration {
    type = "S3"
    s3_configuration {
      bucket_arn = var.s3_arn
    }
  }
}