"""AgentCore client for AWS Bedrock Agent Runtime."""

import requests
import urllib.parse
import json
import uuid


class AgentCoreClient:
    """Client for AWS Bedrock AgentCore Runtime."""

    def __init__(self, agent_runtime_arn: str, region: str):
        self.agent_runtime_arn = agent_runtime_arn
        self.region = region

    def _signed_headers(self, url: str, body: str, extra_headers: dict) -> dict:
        """Sign the request with AWS SigV4 using this machine's own IAM
        credentials, instead of a Cognito JWT Bearer token. The Runtime is
        configured for AWS_IAM auth, not CUSTOM_JWT, so this matches it.
        """
        import boto3
        from botocore.auth import SigV4Auth
        from botocore.awsrequest import AWSRequest

        session = boto3.Session(region_name=self.region)
        credentials = session.get_credentials()

        headers = {"Content-Type": "application/json", **extra_headers}
        request = AWSRequest(method="POST", url=url, data=body, headers=headers)
        SigV4Auth(credentials, "bedrock-agentcore", self.region).add_auth(request)
        return dict(request.headers)

    def create_conversation(self, user_id: str) -> str:
        """Create a new conversation session."""
        return str(uuid.uuid4())

    def send_message(
        self, conversation_id: str, message: str, model: str = None, user_id: str = None
    ) -> dict:
        """Send message to AgentCore and get response."""
        try:
            escaped_agent_arn = urllib.parse.quote(self.agent_runtime_arn, safe="")
            url = f"https://bedrock-agentcore.{self.region}.amazonaws.com/runtimes/{escaped_agent_arn}/invocations?qualifier=DEFAULT"

            payload = {
                "input": {
                    "prompt": message,
                    "conversation_id": conversation_id,
                }
            }

            if user_id:
                payload["input"]["user_id"] = user_id

            body = json.dumps(payload)
            headers = self._signed_headers(
                url, body,
                {"X-Amzn-Bedrock-AgentCore-Runtime-Session-Id": conversation_id},
            )

            response = requests.post(url, headers=headers, data=body, timeout=61)

            if response.status_code == 200:
                result = response.json()
                output = result.get("output", {})
                tools_used_raw = output.get("metadata", {}).get("tools_used", "")
                return {
                    "response": output.get("message", "No response"),
                    "status": "success",
                    "model": output.get("model"),
                    "tools_used": [t.strip() for t in tools_used_raw.split(",") if t.strip()],
                }
            else:
                return {
                    "response": f"Error ({response.status_code}): {response.text}",
                    "status": "error",
                    "tools_used": [],
                }

        except Exception as e:
            return {"response": f"Error: {str(e)}", "status": "error", "tools_used": []}

    def submit_feedback(
        self, run_id: str, session_id: str, score: float, comment: str = ""
    ) -> bool:
        """Submit feedback via AgentCore."""
        try:
            escaped_agent_arn = urllib.parse.quote(self.agent_runtime_arn, safe="")
            url = f"https://bedrock-agentcore.{self.region}.amazonaws.com/runtimes/{escaped_agent_arn}/invocations?qualifier=DEFAULT"

            payload = {
                "input": {
                    "feedback": {
                        "run_id": run_id,
                        "session_id": session_id,
                        "score": score,
                        "comment": comment,
                    }
                }
            }

            body = json.dumps(payload)
            headers = self._signed_headers(
                url, body,
                {"X-Amzn-Bedrock-AgentCore-Runtime-Session-Id": session_id},
            )

            response = requests.post(url, headers=headers, data=body, timeout=30)
            return response.status_code == 200

        except Exception:
            return False
