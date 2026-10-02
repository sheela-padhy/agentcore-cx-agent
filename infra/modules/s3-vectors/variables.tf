variable "name" {
  description = "Base name for the vector bucket and index"
  type        = string
}

variable "dimension" {
  description = "Vector dimension - must match the embedding model's output size (Titan Embed Text v2 = 1024)"
  type        = number
  default     = 1024
}

variable "distance_metric" {
  description = "Distance metric for similarity search - 'cosine' or 'euclidean'. Cosine is AWS's recommended default for Titan text embeddings."
  type        = string
  default     = "cosine"
}

variable "force_destroy" {
  description = "Whether to allow Terraform to destroy the bucket even if it still contains vectors"
  type        = bool
  default     = true
}
