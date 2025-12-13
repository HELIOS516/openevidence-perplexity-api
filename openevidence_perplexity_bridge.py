# Issues and Fixes Summary:
# - The code is generally well-structured but has small issues:
#   - Default environment variable values are not always type-safe
#   - Timeout should be a float everywhere
#   - Minor formatting consistency and constructor signatures
#   - Optional arguments handling should be robust
#   - Environment loading precedence clarification
#   - Main example: No keys supplied; better to allow CLI/env/config for demo
#   - Return types/messages could be more consistent
#   - Add type hints for methods
#   - Protect against missing keys in formatted evidence/citation blocks

# FULLY REVISED CODE FOLLOWS:

import json
import os
from typing import Dict, List, Optional, Any

import requests


class OpenEvidenceClient:
    """Client for interacting with OpenEvidence API"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        search_path: Optional[str] = None,
        payload_key: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        self.api_key = api_key or os.getenv("OPENEVIDENCE_API_KEY")
        self.base_url = base_url or os.getenv("OPENEVIDENCE_BASE_URL", "https://api.openevidence.com")
        self.search_path = search_path or os.getenv("OPENEVIDENCE_SEARCH_PATH", "/search")
        self.payload_key = payload_key or os.getenv("OPENEVIDENCE_PAYLOAD_KEY", "query")
        
        timeout_env = os.getenv("OPENEVIDENCE_TIMEOUT")
        self.timeout: float = 30.0
        if timeout is not None:
            self.timeout = float(timeout)
        elif timeout_env:
            try:
                self.timeout = float(timeout_env)
            except ValueError:
                pass  # keep default

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def search(self, query: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Search OpenEvidence for clinical evidence.

        Args:
            query: Clinical question or search query
            options: Additional search parameters

        Returns:
            Dict containing search results with evidence and citations
        """
        endpoint = f"{self.base_url.rstrip('/')}/{self.search_path.lstrip('/')}"
        payload = {self.payload_key: query}
        if options:
            payload.update(options)

        try:
            response = requests.post(
                endpoint, headers=self.headers, json=payload, timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            http_resp = getattr(e, "response", None)
            extra = ""
            if http_resp is not None and hasattr(http_resp, "status_code"):
                if http_resp.status_code == 404:
                    extra = (
                        " (404 from OpenEvidence endpoint; confirm OPENEVIDENCE_BASE_URL "
                        "and OPENEVIDENCE_SEARCH_PATH)"
                    )
            return {"error": f"{e}{extra}", "status": "failed"}


class PerplexityClient:
    """Client for interacting with Perplexity API"""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or os.getenv("PERPLEXITY_API_KEY")
        self.base_url = base_url or os.getenv("PERPLEXITY_BASE_URL", "https://api.perplexity.ai")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "sonar",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Send chat completion request to Perplexity.

        Args:
            messages: List of message objects
            model: Model to use (default: sonar)
            **kwargs: Additional parameters

        Returns:
            Dict containing Perplexity response
        """
        endpoint = f"{self.base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            **kwargs,
        }

        try:
            response = requests.post(endpoint, headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e), "status": "failed"}


class OpenEvidencePerplexityBridge:
    """
    Bridge between OpenEvidence and Perplexity APIs
    """

    def __init__(
        self,
        openevidence_key: Optional[str] = None,
        perplexity_key: Optional[str] = None
    ):
        self.oe_client = OpenEvidenceClient(api_key=openevidence_key)
        self.perplexity_client = PerplexityClient(api_key=perplexity_key)

    def query_with_evidence(
        self,
        clinical_query: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Query Perplexity with clinical evidence from OpenEvidence.

        Args:
            clinical_query: The clinical question to answer
            context: Additional context for the query

        Returns:
            Dict containing combined response with evidence
        """
        oe_results = self.oe_client.search(clinical_query)

        if "error" in oe_results:
            return {
                "status": "error",
                "message": f"OpenEvidence error: {oe_results['error']}",
            }

        evidence_context = self._format_evidence(oe_results)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a clinical AI assistant with access to evidence-based medical information. "
                    "Use the provided clinical evidence to answer questions accurately."
                ),
            },
            {
                "role": "user",
                "content": f"Clinical Evidence:\n{evidence_context}\n\nQuestion: {clinical_query}",
            },
        ]

        if context:
            messages[1]["content"] = f"{context}\n\n{messages[1]['content']}"

        perplexity_response = self.perplexity_client.chat_completion(messages)

        return {
            "status": "success",
            "query": clinical_query,
            "evidence": oe_results,
            "response": perplexity_response,
            "combined_answer": self._extract_answer(perplexity_response),
        }

    @staticmethod
    def _format_evidence(oe_results: Dict[str, Any]) -> str:
        """Format OpenEvidence results for Perplexity context"""
        if not oe_results or "results" not in oe_results or not oe_results["results"]:
            return "No evidence found."
        formatted = []
        for idx, result in enumerate(oe_results.get("results", [])[:5], 1):
            summary = result.get("summary", "N/A")
            formatted.append(f"{idx}. {summary}")
            citation = result.get("citation")
            if citation:
                formatted.append(f"   Citation: {citation}")
        return "\n".join(formatted)

    @staticmethod
    def _extract_answer(perplexity_response: Dict[str, Any]) -> str:
        """Extract answer from Perplexity response"""
        if not isinstance(perplexity_response, dict):
            return "No answer generated"
        if "error" in perplexity_response:
            return f"Error: {perplexity_response['error']}"
        choices = perplexity_response.get("choices", [])
        if choices and isinstance(choices, list):
            message_dict = choices[0].get("message", {})
            return message_dict.get("content", "No answer generated")
        return "No answer generated"


# Example usage
if __name__ == "__main__":
    # Accept API keys from environment or from command line/config file as needed
    bridge = OpenEvidencePerplexityBridge(
        openevidence_key=os.getenv("OPENEVIDENCE_API_KEY"),
        perplexity_key=os.getenv("PERPLEXITY_API_KEY"),
    )
    query = "What is the recommended treatment for acute myocardial infarction?"
    result = bridge.query_with_evidence(query)
    print(json.dumps(result, indent=2))
