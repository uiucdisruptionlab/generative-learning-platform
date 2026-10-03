# LLM Client

This module owns every LLM and embedding call for all providers. Callers use the Bedrock `converse` / `invoke_model` shape and never talk to a provider SDK directly, so the provider can change without touching prompt code.

`create_llm_client()` picks the provider from the environment, in this order: standard AWS credentials (boto3), `AWS_BEARER_TOKEN_BEDROCK`, then `OPENAI_API_KEY`.

On the OpenAI path the model comes from `OPENAI_MODEL` (default `gpt-4o-mini`) and embeddings from `OPENAI_EMBED_MODEL`. The `modelId` a caller passes is a Bedrock ID and is ignored there, except that `amazon.titan-embed-text*` IDs route to the embeddings endpoint.

A new request option has to be handled in all three clients (boto3, bearer-token Bedrock, OpenAI compat). boto3 rejects unknown `converse` arguments, while the other two silently drop them.
