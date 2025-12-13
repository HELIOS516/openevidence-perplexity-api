# OpenEvidence-Perplexity API Bridge

**Seamless integration between OpenEvidence and Perplexity APIs for clinical evidence-based AI responses**

## Overview

This project provides a Python-based bridge that connects the OpenEvidence API with Perplexity AI, enabling Perplexity to access and utilize clinical evidence from OpenEvidence in its responses. This creates a powerful tool for healthcare professionals and researchers who need AI-powered answers backed by clinical evidence.

## Features

- 🔗 **Seamless API Integration**: Connect OpenEvidence clinical database with Perplexity AI
- 📚 **Evidence-Based Responses**: Perplexity answers enriched with clinical evidence and citations
- 🔒 **Secure Configuration**: Environment-based API key management
- 🎯 **Easy to Use**: Simple Python interface for integration
- 📖 **Well Documented**: Comprehensive documentation and examples

## Architecture

```
┌─────────────────┐
│  Your Application│
└────────┬────────┘
         │
         ▼
┌─────────────────────────────┐
│ OpenEvidencePerplexityBridge│
└──────┬──────────────┬───────┘
       │              │
       ▼              ▼
┌─────────────┐  ┌─────────────┐
│ OpenEvidence│  │ Perplexity  │
│     API     │  │     API     │
└─────────────┘  └─────────────┘
```

## Prerequisites

- Python 3.8 or higher
- OpenEvidence API key (obtain from [OpenEvidence](https://www.openevidence.com))
- Perplexity API key (obtain from [Perplexity](https://www.perplexity.ai))

## Installation

1. **Clone the repository**

```bash
git clone https://github.com/HELIOS516/openevidence-perplexity-api.git
cd openevidence-perplexity-api
```

2. **Install dependencies**

```bash
pip install -r requirements.txt
```

3. **Configure environment variables**

Copy the example environment file and add your API keys:

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```env
OPENEVIDENCE_API_KEY=your_openevidence_api_key_here
OPENEVIDENCE_BASE_URL=https://api.openevidence.com
PERPLEXITY_API_KEY=your_perplexity_api_key_here
```

## Usage

### Basic Example

```python
from openevidence_perplexity_bridge import OpenEvidencePerplexityBridge

# Initialize the bridge
bridge = OpenEvidencePerplexityBridge()

# Query with clinical evidence
query = "What is the recommended treatment for acute myocardial infarction?"
result = bridge.query_with_evidence(query)

# Access the response
print(result['combined_answer'])
print("\nEvidence used:", result['evidence'])
```

### Advanced Example with Context

```python
from openevidence_perplexity_bridge import OpenEvidencePerplexityBridge

bridge = OpenEvidencePerplexityBridge()

# Add context for more specific answers
context = "Patient is 65 years old with diabetes and hypertension"
query = "What are the contraindications for beta-blockers?"

result = bridge.query_with_evidence(query, context=context)
print(result['combined_answer'])
```

### Using Individual Clients

```python
from openevidence_perplexity_bridge import OpenEvidenceClient, PerplexityClient

# Use OpenEvidence client independently
oe_client = OpenEvidenceClient()
evidence = oe_client.search("diabetes treatment guidelines")

# Use Perplexity client independently
perplexity_client = PerplexityClient()
messages = [
    {"role": "user", "content": "Explain diabetes pathophysiology"}
]
response = perplexity_client.chat_completion(messages)
```

## API Reference

### OpenEvidencePerplexityBridge

#### `__init__(openevidence_key=None, perplexity_key=None)`

Initialize the bridge with API keys (optional if set in environment).

#### `query_with_evidence(clinical_query, context=None)`

Query Perplexity with clinical evidence from OpenEvidence.

**Parameters:**
- `clinical_query` (str): The clinical question to answer
- `context` (str, optional): Additional context for the query

**Returns:**
- Dict containing:
  - `status`: 'success' or 'error'
  - `query`: Original query
  - `evidence`: OpenEvidence results
  - `response`: Perplexity API response
  - `combined_answer`: Extracted answer text

### OpenEvidenceClient

#### `search(query, options=None)`

Search OpenEvidence for clinical evidence.

**Parameters:**
- `query` (str): Clinical question or search query
- `options` (dict, optional): Additional search parameters

**Returns:**
- Dict containing search results with evidence and citations

### PerplexityClient

#### `chat_completion(messages, model='sonar', **kwargs)`

Send chat completion request to Perplexity.

**Parameters:**
- `messages` (list): List of message objects
- `model` (str): Model to use (default: 'sonar')
- `**kwargs`: Additional parameters

**Returns:**
- Dict containing Perplexity response

## Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|--------|
| `OPENEVIDENCE_API_KEY` | Your OpenEvidence API key | Yes | - |
| `OPENEVIDENCE_BASE_URL` | OpenEvidence API base URL | No | `https://api.openevidence.com` |
| `OPENEVIDENCE_SEARCH_PATH` | Override the search endpoint path when the API moves (e.g., `/ask_question`) | No | `/search` |
| `OPENEVIDENCE_PAYLOAD_KEY` | Request field that carries the query text (`query`, `question`, etc.) | No | `query` |
| `OPENEVIDENCE_TIMEOUT` | Request timeout in seconds for OpenEvidence calls | No | `30` |
| `PERPLEXITY_API_KEY` | Your Perplexity API key | Yes | - |

## Use Cases

- **Clinical Decision Support**: Get evidence-backed answers for clinical questions
- **Medical Research**: Access clinical evidence with AI-powered synthesis
- **Healthcare Education**: Provide students with evidence-based learning materials
- **Drug Information**: Query drug interactions and treatment guidelines with evidence

## Error Handling

The bridge includes comprehensive error handling:

```python
result = bridge.query_with_evidence(query)

if result['status'] == 'error':
    print(f"Error: {result['message']}")
else:
    print(result['combined_answer'])
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This tool is for informational purposes only and should not be used as a substitute for professional medical advice, diagnosis, or treatment. Always seek the advice of a qualified healthcare provider with any questions you may have regarding a medical condition.

## Support

For issues, questions, or contributions, please open an issue on GitHub.

## Acknowledgments

- [OpenEvidence](https://www.openevidence.com) for providing clinical evidence API
- [Perplexity AI](https://www.perplexity.ai) for AI-powered responses

---

**Built with ❤️ for better healthcare decision-making**
