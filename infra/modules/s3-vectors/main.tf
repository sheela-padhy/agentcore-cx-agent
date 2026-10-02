resource "aws_s3vectors_vector_bucket" "kb_vectors" {
  vector_bucket_name = "s3vec-${var.name}"
  force_destroy      = var.force_destroy
  # encryption_configuration omitted deliberately - it's optional+computed,
  # AWS applies its own default (SSE-S3/AES256) if not specified, and its
  # real HCL type is list(object(...)) (an attribute, not a classic nested
  # block), which is easy to get wrong - simplest to just not set it.
}

resource "aws_s3vectors_index" "kb_vector_index" {
  vector_bucket_name = aws_s3vectors_vector_bucket.kb_vectors.vector_bucket_name
  index_name         = "s3vec-index-${var.name}"
  data_type          = "float32"
  dimension          = var.dimension
  distance_metric    = var.distance_metric
}
