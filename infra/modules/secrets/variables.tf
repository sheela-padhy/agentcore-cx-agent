variable "cognito_client_secret" {
  description = "Cognito client secret"
  type        = string
  sensitive   = true
}

variable "zendesk_domain" {
  description = "Zendesk subdomain"
  type        = string
}

variable "zendesk_oauth_client_id" {
  description = "Zendesk OAuth client unique identifier"
  type        = string
}

variable "zendesk_oauth_client_secret" {
  description = "Zendesk OAuth client secret"
  type        = string
  sensitive   = true
}

variable "zendesk_oauth_refresh_token" {
  description = "Zendesk OAuth refresh token (initial value - rotated by the backend thereafter)"
  type        = string
  sensitive   = true
}

variable "langfuse_host" {
  description = "Langfuse host"
  type        = string
}

variable "langfuse_public_key" {
  description = "Langfuse public key"
  type        = string
}

variable "langfuse_secret_key" {
  description = "Langfuse secret key"
  type        = string
  sensitive   = true
}

variable "gateway_url" {
  description = "Gateway URL"
  type        = string
}

variable "gateway_api_key" {
  description = "Gateway API key"
  type        = string
  sensitive   = true
}

variable "kms_key_id" {
  description = "KMS key ID for encrypting secrets"
  type        = string
  default     = null
}
variable "tavily_api_key" {
  description = "Tavily API key for web search"
  type        = string
  default     = ""
  sensitive   = true
}
