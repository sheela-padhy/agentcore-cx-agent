resource "aws_bedrock_guardrail" "guardrail" {
  name                      = var.guardrail_name
  blocked_input_messaging   = var.blocked_input_messaging
  blocked_outputs_messaging = var.blocked_outputs_messaging
  description               = var.description

  content_policy_config {
    filters_config {
      input_strength  = "MEDIUM"
      output_strength = "MEDIUM"
      type            = "HATE"
    }
  }

  sensitive_information_policy_config {
    # input_enabled / output_enabled are "optional, computed" in the AWS
    # provider schema - when left unset, AWS silently defaults them to
    # disabled, so the entity shows up as "configured" (action=ANONYMIZE)
    # in GetGuardrail but ApplyGuardrail never actually scans for it
    # (sensitiveInformationPolicyUnits stays 0 on every call). They must
    # be set explicitly to turn the entity on.
    pii_entities_config {
      action         = "ANONYMIZE"
      type           = "US_BANK_ROUTING_NUMBER"
      input_enabled  = true
      input_action   = "ANONYMIZE"
      output_enabled = true
      output_action  = "ANONYMIZE"
    }

    pii_entities_config {
      action         = "ANONYMIZE"
      type           = "US_SOCIAL_SECURITY_NUMBER"
      input_enabled  = true
      input_action   = "ANONYMIZE"
      output_enabled = true
      output_action  = "ANONYMIZE"
    }
  }

  topic_policy_config {
    topics_config {
      name       = "investment_topic"
      examples   = ["Where should I invest my money ?"]
      type       = "DENY"
      definition = "Investment advice refers to inquiries, guidance, or recommendations regarding the management or allocation of funds or assets with the goal of generating returns ."
    }
  }

  word_policy_config {
    managed_word_lists_config {
      type = "PROFANITY"
    }
    words_config {
      text = "HATE"
    }
  }
}