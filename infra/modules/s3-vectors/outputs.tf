output "vector_bucket_arn" {
  description = "ARN of the S3 Vectors bucket"
  value       = aws_s3vectors_vector_bucket.kb_vectors.vector_bucket_arn
}

output "vector_bucket_name" {
  description = "Name of the S3 Vectors bucket"
  value       = aws_s3vectors_vector_bucket.kb_vectors.vector_bucket_name
}

output "index_arn" {
  description = "ARN of the S3 Vectors index"
  value       = aws_s3vectors_index.kb_vector_index.index_arn
}

output "index_name" {
  description = "Name of the S3 Vectors index"
  value       = aws_s3vectors_index.kb_vector_index.index_name
}
