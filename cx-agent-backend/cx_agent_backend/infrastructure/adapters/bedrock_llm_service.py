"""Bedrock implementation of LLM service — calls Claude directly via
AWS Bedrock using this instance's own IAM role. No gateway, no API key.
"""

from langchain_aws import ChatBedrockConverse
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from cx_agent_backend.domain.entities.conversation import MessageRole
from cx_agent_backend.domain.services.llm_service import (
    LLMRequest,
    LLMResponse,
    LLMService,
)


class BedrockLLMService(LLMService):
    """Bedrock implementation of LLM service."""

    def __init__(self, model: str, region: str = "us-west-2"):
        self.model_id = model
        self._client = ChatBedrockConverse(
            model=model,
            region_name=region,
            temperature=0.7,
        )

    def _to_langchain_messages(self, messages):
        lc_messages = []
        for msg in messages:
            if msg.role == MessageRole.USER:
                lc_messages.append(HumanMessage(content=msg.content))
            elif msg.role == MessageRole.ASSISTANT:
                lc_messages.append(AIMessage(content=msg.content))
            elif msg.role == MessageRole.SYSTEM:
                lc_messages.append(SystemMessage(content=msg.content))
        return lc_messages

    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """Generate response using Bedrock."""
        lc_messages = self._to_langchain_messages(request.messages)
        response = await self._client.ainvoke(lc_messages)

        return LLMResponse(
            content=response.content,
            model=request.model,
            usage_tokens=response.response_metadata.get("usage", {}).get(
                "total_tokens", 0
            ),
            metadata=response.response_metadata,
        )

    async def stream_response(self, request: LLMRequest):
        """Stream response using Bedrock."""
        lc_messages = self._to_langchain_messages(request.messages)
        async for chunk in self._client.astream(lc_messages):
            if chunk.content:
                yield chunk.content
