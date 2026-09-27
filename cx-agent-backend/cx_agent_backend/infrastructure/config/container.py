"""Dependency injection container."""

from dependency_injector import containers, providers

from cx_agent_backend.domain.services.conversation_service import ConversationService
from cx_agent_backend.infrastructure.adapters.memory_conversation_repository import (
    MemoryConversationRepository,
)
from cx_agent_backend.infrastructure.adapters.langgraph_agent_service import (
    LangGraphAgentService,
)
from cx_agent_backend.infrastructure.adapters.bedrock_guardrail_service import (
    BedrockGuardrailService,
)
from cx_agent_backend.infrastructure.adapters.bedrock_llm_service import (
    BedrockLLMService,
)
from cx_agent_backend.infrastructure.config.settings import settings
from cx_agent_backend.infrastructure.aws.parameter_store_reader import (
    AWSParameterStoreReader,
)


class Container(containers.DeclarativeContainer):
    """Dependency injection container."""

    # Configuration
    config = providers.Configuration()
    parameter_store_reader = AWSParameterStoreReader()

    # Repositories
    conversation_repository = providers.Singleton(MemoryConversationRepository)

    # Services
    guardrail_service = (
        providers.Singleton(
            BedrockGuardrailService,
            guardrail_id=parameter_store_reader.get_parameter(
                "/amazon/guardrail_id", decrypt=True
            ),
            region=settings.aws_region,
        )
        if settings.guardrails_enabled
        else providers.Object(None)
    )

    # Calls Claude directly via Bedrock, using this Runtime's own IAM
    # role — no GenAI Gateway, no separate API key needed.
    llm_service = providers.Singleton(
        BedrockLLMService,
        model=settings.default_model,
        region=settings.aws_region,
    )

    agent_service = providers.Singleton(
        LangGraphAgentService,
        guardrail_service=guardrail_service,
        llm_service=llm_service,
    )

    conversation_service = providers.Factory(
        ConversationService,
        conversation_repo=conversation_repository,
        agent_service=agent_service,
        guardrail_service=guardrail_service,
    )
