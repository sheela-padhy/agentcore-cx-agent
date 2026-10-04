"""Tools for agent operations."""

import boto3
from langchain_core.tools import tool
import logging
import json

from cx_agent_backend.infrastructure.config.settings import settings
from cx_agent_backend.infrastructure.aws.secret_reader import AWSSecretsReader
from cx_agent_backend.infrastructure.aws.parameter_store_reader import (
    AWSParameterStoreReader,
)

# Configure logging for local development
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


secret_reader = AWSSecretsReader()
parameter_store_reader = AWSParameterStoreReader()


@tool
def retrieve_context(query: str) -> dict:
    """Retrieve context from the Knowledge Base to answer frequently asked questions."""
    logger.info("Retrieving context for query: %s...", query[:100])

    try:
        kb_id = parameter_store_reader.get_parameter("/amazon/kb_id", decrypt=True)
        if not kb_id:
            logger.error("Bedrock Knowledge Base ID not configured in parameter store")
            raise ValueError("Bedrock Knowledge Base ID not configured")

        # Call Bedrock's Retrieve API directly with plain boto3, bypassing
        # the AmazonKnowledgeBasesRetriever wrapper, which was silently
        # returning zero results despite the underlying API working fine.
        client = boto3.client("bedrock-agent-runtime", region_name=settings.aws_region)
        response = client.retrieve(
            knowledgeBaseId=kb_id,
            retrievalQuery={"text": query},
            retrievalConfiguration={
                "vectorSearchConfiguration": {"numberOfResults": 3}
            },
        )
        results = response.get("retrievalResults", [])
        logger.info("Retrieved %s documents from knowledge base", len(results))

        document_summaries = []
        citations = []

        for i, result in enumerate(results, 1):
            content_text = result.get("content", {}).get("text", "")
            s3_uri = result.get("location", {}).get("s3Location", {}).get("uri", "")
            score = result.get("score", 0)
            title = s3_uri.rsplit("/", 1)[-1] if s3_uri else f"Document {i}"

            summary = {
                "id": f"doc-{i}",
                "source": s3_uri or "Unknown",
                "title": title,
                "content": content_text,
                "relevance_score": score,
                "s3_uri": s3_uri,
                "knowledge_base_id": kb_id,
            }
            document_summaries.append(summary)

            citation = {
                "source": title,
                "s3_uri": s3_uri,
                "knowledge_base_id": kb_id,
                "relevance_score": score,
            }
            citations.append(citation)
            print(json.dumps(citation))

            logger.debug("Processed document %s: %s...", i, title[:50])

        logger.info(
            "Successfully retrieved and processed %s documents", len(document_summaries)
        )
        return {
            "retrieved_documents": document_summaries,
            "citations": citations,
            "knowledge_base_id": kb_id,
        }

    except Exception as e:
        logger.error("Failed to retrieve context: %s", str(e))
        return {
            "retrieved_documents": [],
            "citations": [],
            "error": f"Knowledge base retrieval failed: {str(e)}",
        }


def _get_zendesk_access_token() -> dict | None:
    """Exchange the stored Zendesk refresh_token for a fresh access_token.

    Zendesk's OAuth tokens are short-lived (access_token ~30 min) and the
    refresh_token itself is single-use - every refresh call returns a NEW
    refresh_token and invalidates the old one. So this isn't a one-time
    setup: every real call has to refresh first, then immediately persist
    the newly-issued refresh_token back to Secrets Manager, or the next
    call will fail with invalid_grant.

    Returns None (triggering the mock fallback) if Zendesk isn't configured
    or the refresh fails for any reason.
    """
    import requests

    try:
        creds = json.loads(secret_reader.read_secret("zendesk_credentials"))
        domain = creds.get("zendesk_domain")
        client_id = creds.get("zendesk_oauth_client_id")
        client_secret = creds.get("zendesk_oauth_client_secret")
        refresh_token = creds.get("zendesk_oauth_refresh_token")
    except Exception:
        logger.error("Failed to retrieve Zendesk credentials")
        return None

    if not all([domain, client_id, client_secret, refresh_token]):
        return None

    try:
        response = requests.post(
            f"https://{domain}.zendesk.com/oauth/tokens",
            json={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": client_id,
                "client_secret": client_secret,
            },
            timeout=30,
        )
        response.raise_for_status()
        token_data = response.json()
    except Exception as e:
        logger.error("Zendesk OAuth token refresh failed: %s", str(e))
        return None

    try:
        creds["zendesk_oauth_refresh_token"] = token_data["refresh_token"]
        boto3.client(
            "secretsmanager", region_name=settings.aws_region
        ).put_secret_value(
            SecretId="zendesk_credentials", SecretString=json.dumps(creds)
        )
    except Exception as e:
        # The access_token below still works for this one call, but the
        # NEXT refresh will fail since Zendesk already invalidated the old
        # refresh_token server-side. Log loudly so this doesn't go unnoticed.
        logger.error(
            "Got a new Zendesk access_token but failed to persist the "
            "rotated refresh_token - the next Zendesk call will likely "
            "fail until this is fixed: %s",
            str(e),
        )

    return {"domain": domain, "access_token": token_data["access_token"]}


@tool
def create_support_ticket(
    subject: str,
    description: str,
    requester_name: str = None,
    requester_email: str = None,
    priority: str = "normal",
) -> dict:
    """Create a support ticket in Zendesk."""
    import requests
    import uuid

    logger.info("Creating support ticket with subject: %s...", subject[:50])
    logger.debug(
        "Ticket details - Priority: %s, Requester: %s (%s)",
        priority,
        requester_name or "N/A",
        requester_email or "N/A",
    )

    zendesk = _get_zendesk_access_token()

    # If credentials not configured / refresh failed, return mock response
    if not zendesk:
        logger.warning("Zendesk credentials not configured, returning mock response")
        ticket_id = str(uuid.uuid4())[:8]
        mock_response = {
            "ticket": {
                "id": ticket_id,
                "subject": subject,
                "description": description,
                "status": "new",
                "priority": priority,
                "requester": {
                    "name": requester_name or "Customer",
                    "email": requester_email or "customer@example.com",
                },
            }
        }
        logger.info("Mock ticket created with ID")
        return mock_response

    # Real Zendesk integration
    logger.info("Attempting to create real Zendesk ticket")
    subdomain = zendesk["domain"]
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {zendesk['access_token']}",
    }

    ticket_data = {
        "subject": subject,
        "comment": {"body": description},
        "priority": priority,
    }

    if requester_email or requester_name:
        ticket_data["requester"] = {}
        if requester_email:
            ticket_data["requester"]["email"] = requester_email
        if requester_name:
            ticket_data["requester"]["name"] = requester_name
        logger.debug("Added requester info to ticket data")

    try:
        url = f"https://{subdomain}.zendesk.com/api/v2/tickets.json"
        logger.debug("Making POST request to Zendesk API endpoint")

        response = requests.post(
            url, headers=headers, data=json.dumps({"ticket": ticket_data}), timeout=61
        )

        logger.info("Zendesk API response status: %s", response.status_code)
        response.raise_for_status()

        result = response.json()
        ticket_id = result.get("ticket", {}).get("id", "unknown")
        logger.info("Successfully created Zendesk ticket with ID")

        return result
    except requests.exceptions.RequestException as e:
        logger.error("Zendesk API request failed: %s", str(e))
        return {"error": f"Failed to create ticket: {str(e)}"}
    except Exception as e:
        logger.error("Unexpected error creating ticket: %s", str(e))
        return {"error": f"Failed to create ticket: {str(e)}"}


@tool
def get_support_tickets(
    status: str = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    limit: int = 25,
) -> dict:
    """Fetch tickets from Zendesk with optional filtering."""
    import requests

    logger.info(
        "Fetching support tickets - Status: %s, Limit: %s", status or "all", limit
    )
    logger.debug("Sort parameters - By: %s, Order: %s", sort_by, sort_order)

    zendesk = _get_zendesk_access_token()

    # If credentials not configured / refresh failed, return mock response
    if not zendesk:
        logger.warning("Zendesk credentials not configured, returning mock tickets")
        mock_response = {
            "tickets": [
                {
                    "id": "12345",
                    "subject": "Sample Ticket",
                    "status": "open",
                    "priority": "normal",
                    "created_at": "2024-01-01T00:00:00Z",
                }
            ]
        }
        logger.info("Returned 1 mock ticket")
        return mock_response

    # Real Zendesk integration
    logger.info("Fetching tickets from Zendesk API")
    subdomain = zendesk["domain"]
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {zendesk['access_token']}",
    }

    params = {"sort_by": sort_by, "sort_order": sort_order, "per_page": min(limit, 100)}
    if status:
        params["status"] = status
        logger.debug("Filtering by status: %s", status)

    try:
        url = f"https://{subdomain}.zendesk.com/api/v2/tickets.json"
        logger.debug("Making GET request to Zendesk tickets API endpoint")

        response = requests.get(url, headers=headers, params=params, timeout=61)
        logger.info("Zendesk API response status: %s", response.status_code)

        response.raise_for_status()
        result = response.json()

        ticket_count = len(result.get("tickets", []))
        logger.info("Successfully fetched %s tickets from Zendesk", ticket_count)

        return result
    except requests.exceptions.RequestException as e:
        logger.error("Zendesk API request failed: %s", str(e))
        return {"error": f"Failed to fetch tickets: {str(e)}"}
    except Exception as e:
        logger.error("Unexpected error fetching tickets: %s", str(e))
        return {"error": f"Failed to fetch tickets: {str(e)}"}


@tool
def web_search(query: str) -> str:
    """Search the web for information using Tavily API."""
    logger.info("Performing web search for query: %s...", query[:100])

    try:
        tavily_secret = secret_reader.read_secret("tavily_key")
        tavily_api_key = json.loads(tavily_secret)["tavily_key"]
        logger.debug("Retrieved Tavily API credentials")
    except Exception:
        logger.error("Failed to retrieve Tavily credentials")
        tavily_api_key = None

    # If API key not configured, return mock response
    if not tavily_api_key:
        logger.warning("Tavily API key not configured, returning mock search results")
        mock_result = f"Mock search results for: {query}. Configure TAVILY_API_KEY for real web search."
        logger.info("Returned mock web search results")
        return mock_result

    try:
        from tavily import TavilyClient

        logger.debug("Tavily client imported successfully")

        client = TavilyClient(api_key=tavily_api_key)
        logger.debug("Tavily client initialized")

        response = client.search(query)
        logger.info("Web search completed successfully for query: %s...", query[:50])

        # Log response summary without full content
        if isinstance(response, dict) and "results" in response:
            result_count = len(response.get("results", []))
            logger.debug("Web search returned %s results", result_count)

        return str(response)
    except ImportError as e:
        logger.error("Tavily client not installed: %s", str(e))
        return f"Tavily client not installed. Mock results for: {query}"
    except Exception as e:
        logger.error("Web search failed: %s", str(e))
        return f"Web search failed: {str(e)}"


# Available tools
tools = [
    web_search,
    retrieve_context,
    create_support_ticket,
    get_support_tickets,
]
