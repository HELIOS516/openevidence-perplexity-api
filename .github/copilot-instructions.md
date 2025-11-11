# AI Coding Agent Instructions for OpenEvidence-Perplexity API Bridge

## Project Overview

This is a lightweight Python bridge that integrates two external APIs: **OpenEvidence** (clinical evidence database) and **Perplexity** (AI chat service). The core responsibility is orchestrating API calls between these services to deliver evidence-backed clinical answers.

## Architecture & Key Components

### Three-Tier Client Design

The codebase follows a clear separation of concerns in `openevidence_perplexity_bridge.py`:

1. **OpenEvidenceClient**: Wrapper around OpenEvidence REST API
   - Handles evidence searches with `search(query, options)`
   - Returns structured clinical evidence results with citations
   - Error handling returns `{"error": str, "status": "failed"}`

2. **PerplexityClient**: Wrapper around Perplexity REST API
   - Executes chat completions with `chat_completion(messages, model)`
   - Accepts system/user message patterns
   - Supports custom model selection (default: 'sonar')

3. **OpenEvidencePerplexityBridge**: Orchestration layer
   - `query_with_evidence()` is the main entry point
   - 5-step workflow: (1) Search OpenEvidence, (2) Format evidence, (3) Build messages, (4) Query Perplexity, (5) Extract/combine response

### Data Flow Pattern

```
User Query → OpenEvidenceClient.search() 
           → _format_evidence() (top 5 results)
           → Inject into system prompt
           → PerplexityClient.chat_completion()
           → _extract_answer() from choices[0].message.content
           → Return combined result dict
```

## Critical Workflows & Commands

### Development Setup
```bash
pip install -r requirements.txt
# Dependencies: requests (HTTP), python-dotenv (env loading)
```

### Testing/Validation
- No test framework configured; validation is manual or via direct `python openevidence_perplexity_bridge.py`
- The `if __name__ == "__main__"` block provides a runnable example
- To test: `python openevidence_perplexity_bridge.py` requires valid API keys in `.env`

### Documentation Build
- Uses Sphinx with RTD theme
- Location: `docs/conf.py` 
- Supports both `.rst` and `.md` via myst_parser
- Auto-generates from docstrings with napoleon extension

## Configuration & Secrets

### Environment Variables
Must be set in `.env` (see `.env.example`):
- `OPENEVIDENCE_API_KEY` (required)
- `PERPLEXITY_API_KEY` (required)
- `OPENEVIDENCE_BASE_URL` (optional; defaults to https://api.openevidence.com)

**Client initialization defaults to environment variables** if not passed as constructor arguments:
```python
# Constructor can override, but defaults to env:
bridge = OpenEvidencePerplexityBridge(openevidence_key="...", perplexity_key="...")
```

### API Headers Pattern
Both clients use Bearer token auth:
```python
self.headers = {
    "Authorization": f"Bearer {self.api_key}",
    "Content-Type": "application/json",
}
```

## Patterns & Conventions

### Error Handling Strategy
- **API errors**: Caught with `requests.exceptions.RequestException`
- **Response format**: Return dict with `"error"` key instead of raising exceptions
- **Example**: Search fails → returns `{"error": str(e), "status": "failed"}`
- **Client responsibility**: Callers check for `"error"` key before processing

### Message Protocol for PerplexityClient
Expects standard chat completion format:
```python
messages = [
    {"role": "system", "content": "system instruction"},
    {"role": "user", "content": "user query"},
]
```

### Evidence Formatting
`_format_evidence()` handles OpenEvidence response structure:
- Takes top 5 results (hard-coded limit)
- Extracts `summary` field and optional `citation`
- Returns numbered markdown-like text for prompt injection

### Response Extraction
`_extract_answer()` assumes Perplexity response structure:
- Looks for `choices[0].message.content`
- Gracefully handles missing fields
- Returns error string if present

## Integration Points & External Dependencies

### OpenEvidence API
- **Endpoint**: `{OPENEVIDENCE_BASE_URL}/search`
- **Method**: POST
- **Payload**: `{"query": str, ...options}`
- **Assumption**: Returns `{"results": [{"summary": str, "citation": str}]}`
- **Reliability**: Errors are caught, not fatal to application

### Perplexity API
- **Endpoint**: `https://api.perplexity.ai/chat/completions`
- **Method**: POST
- **Models**: 'sonar' is default; client accepts arbitrary model param
- **Assumption**: Follows OpenAI chat completion schema

### Request Library Usage
- Simple `requests.post()` with headers and JSON payloads
- `response.raise_for_status()` converts HTTP errors to exceptions
- No retry logic; single attempt per call

## Extension Points

When adding features, follow these patterns:

1. **New search parameters**: Update `OpenEvidenceClient.search()` options merging
2. **New models/features**: Extend `PerplexityClient.chat_completion()` **kwargs pattern
3. **Response processing**: Add methods to Bridge class (prefix with `_` for internal)
4. **Evidence filtering**: Modify `_format_evidence()` or create `_filter_evidence()`
5. **Message customization**: Update prompt construction in `query_with_evidence()`

## Documentation Standards

- Docstrings use Google-style format (processed by napoleon in Sphinx)
- Include Args, Returns sections with type hints
- Module-level docstring explains purpose
- Inline comments clarify non-obvious logic (e.g., top 5 result limit, Bearer token format)
