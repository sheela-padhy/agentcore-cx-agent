# What's different from the original AWS blueprint

This project started as a fork of AWS's own [`agentcore-samples`](https://github.com/awslabs/agentcore-samples) tutorial blueprint. If you're starting fresh, you don't need any of this — the main [README](README.md) is a complete, self-contained guide on its own. This file exists only for anyone who already knows the original blueprint and wants to know exactly what changed and why.

| Original design | This fork | Why |
|---|---|---|
| Routes every model call through a self-hosted **GenAI Gateway** (LiteLLM) | Calls **Amazon Bedrock directly** | The Gateway costs ~$380/month to run, just for routing — not worth it for a single agent. Direct calls are simpler, at the cost of losing cross-project governance/rate-limiting (a reasonable trade at this scale). |
| Knowledge Base backed by **OpenSearch Serverless** | Backed by **Amazon S3 Vectors** | OpenSearch Serverless had a real, reproducible bug: its internal "collection" layer silently failed to allocate shards, so retrieval always returned zero results, no error. S3 Vectors has no collection/shard concept at all — simpler, and cheaper too. |
| Manual deployment (`terraform apply`, then manually clicking "Update hosting" in the console) | **Full CI/CD**: push code → automated checks → merge → automatic build, tag, and redeploy | A real pipeline, not a checklist — see [Architecture](README.md#architecture) in the main README. |
| Auth via JWT bearer tokens | **AWS IAM / SigV4 signing** | Matches how AWS's own tools authenticate; one fewer custom auth system to maintain. |
| Zendesk via API token | **Zendesk via OAuth2** | Zendesk is sunsetting API tokens (removed for new trial accounts already). The agent refreshes its access token before every real call and persists the rotated refresh token back to Secrets Manager automatically - see `_get_zendesk_access_token()` in `tools.py`. |
