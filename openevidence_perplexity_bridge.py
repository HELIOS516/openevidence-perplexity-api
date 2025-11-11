"""
OpenEvidence-Perplexity API Bridge

This module provides a seamless interface between OpenEvidence API and Perplexity API,
allowing Perplexity to access clinical evidence-based information from OpenEvidence.
"""

import json
import os
from typing import Dict, List, Optional

import requests


class OpenEvidenceClient:
    """Client for interacting with OpenEvidence API"""

    def __init__(self, api_key: str = None, base_url: str = None):
        self.api_key = api_key or os.getenv("OPENEVIDENCE_API_KEY")
        self.base_url = base_url or os.getenv("OPENEVIDENCE_BASE_URL", "https://api.openevidence.com")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def search(self, query: str, options: Optional[Dict] = None) -> Dict:
        """
        Search OpenEvidence for clinical evidence

        Args:
            query: Clinical question or search query
            options: Additional search parameters

        Returns:
            Dict containing search results with evidence and citations
        """
        endpoint = f"{self.base_url}/search"
        payload = {"query": query}
        if options:
            payload.update(options)

        try:
            response = requests.post(endpoint, headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e), "status": "failed"}


class PerplexityClient:
    """Client for interacting with Perplexity API"""

    def __init__(self, api_key: str = None, base_url: str = None):
        self.api_key = api_key or os.getenv("PERPLEXITY_API_KEY")
        self.base_url = base_url or "https://api.perplexity.ai"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def chat_completion(self, messages: List[Dict], model: str = "sonar", **kwargs) -> Dict:
        """
        Send chat completion request to Perplexity

        Args:
            messages: List of message objects
            model: Model to use (default: sonar)
            **kwargs: Additional parameters

        Returns:
            Dict containing Perplexity response
        """
        endpoint = f"{self.base_url}/chat/completions"
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
    """Bridge between OpenEvidence and Perplexity APIs"""

    def __init__(self, openevidence_key: str = None, perplexity_key: str = None):
        self.oe_client = OpenEvidenceClient(api_key=openevidence_key)
        self.perplexity_client = PerplexityClient(api_key=perplexity_key)

    def query_with_evidence(self, clinical_query: str, context: Optional[str] = None) -> Dict:
        """
        Query Perplexity with clinical evidence from OpenEvidence

        Args:
            clinical_query: The clinical question to answer
            context: Additional context for the query

        Returns:
            Dict containing combined response with evidence
        """
        # Step 1: Get evidence from OpenEvidence
        oe_results = self.oe_client.search(clinical_query)

        if "error" in oe_results:
            return {
                "status": "error",
                "message": f"OpenEvidence error: {oe_results['error']}",
            }

        # Step 2: Format evidence for Perplexity
        evidence_context = self._format_evidence(oe_results)

        # Step 3: Construct Perplexity prompt with evidence
        messages = [
            {
                "role": "system",
                "content": "You are a clinical AI assistant with access to evidence-based medical information. Use the provided clinical evidence to answer questions accurately.",
            },
            {
                "role": "user",
                "content": f"Clinical Evidence:\n{evidence_context}\n\nQuestion: {clinical_query}",
            },
        ]

        if context:
            messages[1]["content"] = f"{context}\n\n{messages[1]['content']}"

        # Step 4: Get Perplexity response
        perplexity_response = self.perplexity_client.chat_completion(messages)

        # Step 5: Combine results
        return {
            "status": "success",
            "query": clinical_query,
            "evidence": oe_results,
            "response": perplexity_response,
            "combined_answer": self._extract_answer(perplexity_response),
        }

    def _format_evidence(self, oe_results: Dict) -> str:
        """Format OpenEvidence results for Perplexity context"""
        if not oe_results or "results" not in oe_results:
            return "No evidence found."

        formatted = []
        for idx, result in enumerate(oe_results.get("results", [])[:5], 1):
            formatted.append(f"{idx}. {result.get('summary', 'N/A')}")
            if "citation" in result:
                formatted.append(f"   Citation: {result['citation']}")

        return "\n".join(formatted)

    def _extract_answer(self, perplexity_response: Dict) -> str:
        """Extract answer from Perplexity response"""
        if "error" in perplexity_response:
            return f"Error: {perplexity_response['error']}"

        choices = perplexity_response.get("choices", [])
        if choices:
            return choices[0].get("message", {}).get("content", "No answer generated")
        return "No answer generated"


# Example usage
if __name__ == "__main__":
    bridge = OpenEvidencePerplexityBridge()
    query = "What is the recommended treatment for acute myocardial infarction?"
    result = bridge.query_with_evidence(query)
    print(json.dumps(result, indent=2))
