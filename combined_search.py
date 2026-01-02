from __future__ import annotations

import argparse
import os
import textwrap
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional
from urllib.parse import urljoin

import requests
from dotenv import load_dotenv
from perplexity import Perplexity
from requests import Response

load_dotenv()

TRAUMA_CRITICAL_CARE_PROFILE = """You are supporting trauma-critical care attendings at a level-one trauma center.
Deliver high-level, data-driven evidence syntheses that emphasize:
- early resuscitation, hemostasis, neuroprotection, and critical care bundle adherence
- guideline concordance (EAST, WTA, SCCM, AABB, TQIP) and recent randomized/observational evidence
- applicability to polytrauma and ICU populations, including comorbidities and resource constraints
State uncertainty, cite sources, and flag when more evidence is required."""


@dataclass
class SearchHit:
    title: str
    url: str
    snippet: str
    engine: str
    source: Optional[str] = None
    metadata: Dict[str, Optional[str]] = field(default_factory=dict)

    def clipped_snippet(self, max_length: int = 320) -> str:
        snippet = (self.snippet or "").strip()
        if len(snippet) <= max_length:
            return snippet
        return snippet[: max_length - 1].rstrip() + "…"


class PerplexityClient:
    """Wrapper around the official Perplexity Python SDK."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        default_chat_model: Optional[str] = None,
    ) -> None:
        self.api_key = api_key or os.getenv("PERPLEXITY_API_KEY")
        if not self.api_key:
            raise RuntimeError(
                "Missing PERPLEXITY_API_KEY. Add it to your environment or .env file."
            )

        self.client = Perplexity(api_key=self.api_key)
        self.chat_model = default_chat_model or os.getenv(
            "PERPLEXITY_CHAT_MODEL", "sonar"
        )

    def search(self, query: str, max_results: int = 5) -> List[SearchHit]:
        payload = {"query": query, "max_results": max_results}

        response = self.client.search.create(**payload)
        hits = []
        for item in response.results:
            hits.append(
                SearchHit(
                    title=item.title or "Untitled",
                    url=item.url,
                    snippet=item.snippet or "",
                    engine="perplexity-search",
                    source=item.last_updated or item.date,
                )
            )
        return hits

    def synthesize_answer(
        self,
        question: str,
        context_hits: Iterable[SearchHit],
        *,
        include_open_evidence: bool,
        temperature: float = 0.1,
        max_tokens: int = 1200,
    ) -> str:
        context = self._format_hits_for_prompt(context_hits, include_open_evidence)

        response = self.client.chat.completions.create(
            model=self.chat_model,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": TRAUMA_CRITICAL_CARE_PROFILE},
                {
                    "role": "user",
                    "content": (
                        f"Clinical question: {question.strip()}\n\n"
                        f"Evidence packets:\n{context}\n\n"
                        "Deliver a concise, evidence-grounded synthesis with citations."
                    ),
                },
            ],
        )

        if not response.choices:
            return "No summary available."

        content = response.choices[0].message.content
        if isinstance(content, str):
            return content.strip()

        chunks = []
        for chunk in content or []:
            if isinstance(chunk, dict) and chunk.get("type") == "text":
                chunks.append(chunk.get("text", ""))
        return "\n".join(filter(None, chunks)).strip() or "No summary available."

    @staticmethod
    def _format_hits_for_prompt(
        hits: Iterable[SearchHit], include_open_evidence: bool
    ) -> str:
        lines = []
        for idx, hit in enumerate(hits, start=1):
            origin = hit.engine.replace("-", " ").title()
            lines.append(
                textwrap.dedent(
                    f"""\
                    [{idx}] ({origin})
                    Title: {hit.title}
                    URL: {hit.url}
                    Summary: {hit.snippet.strip()}
                    """
                ).strip()
            )

        suffix = (
            "\nInclude OpenEvidence considerations when prioritizing recommendations."
            if include_open_evidence
            else ""
        )
        return "\n\n".join(lines) + suffix


class OpenEvidenceClient:
    """Lightweight REST client for the OpenEvidence API."""

    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        token: Optional[str] = None,
        auth_scheme: Optional[str] = None,
        search_path: Optional[str] = None,
        timeout: float = 30.0,
    ) -> None:
        default_base = "https://api.openevidence.com"
        self.base_url = (
            (base_url or os.getenv("OPEN_EVIDENCE_BASE_URL", default_base))
        ).rstrip("/")
        self.token = token or os.getenv("OPEN_EVIDENCE_API_TOKEN")
        self.auth_scheme = auth_scheme or os.getenv(
            "OPEN_EVIDENCE_AUTH_SCHEME", "Bearer"
        )
        self.search_path = search_path or os.getenv(
            "OPEN_EVIDENCE_SEARCH_PATH", "/ask_question"
        )
        self.timeout = timeout
        self.session = requests.Session()

    @property
    def is_configured(self) -> bool:
        return bool(self.base_url and self.token)

    def search(self, query: str, max_results: int = 5) -> List[SearchHit]:
        if not self.is_configured:
            raise RuntimeError(
                "OpenEvidence client is not configured. "
                "Set OPEN_EVIDENCE_BASE_URL and OPEN_EVIDENCE_API_TOKEN."
            )

        url = urljoin(f"{self.base_url}/", self.search_path.lstrip("/"))
        payload = {"question": query, "max_docs": max_results}
        headers = {
            "Authorization": f"{self.auth_scheme} {self.token}",
            "Content-Type": "application/json",
        }

        response = self.session.post(
            url, json=payload, headers=headers, timeout=self.timeout
        )
        self._raise_for_status(response)
        body = response.json()
        data_section = body.get("data") if isinstance(body, dict) else None

        if isinstance(data_section, dict):
            raw_results = (
                data_section.get("sources")
                or data_section.get("results")
                or data_section.get("documents")
                or []
            )
        else:
            raw_results = body.get("results") or []

        hits = []
        if isinstance(raw_results, dict):
            raw_results = [raw_results]

        for idx, item in enumerate(raw_results or [], start=1):
            hits.append(
                SearchHit(
                    title=item.get("title") or item.get("source") or f"OpenEvidence #{idx}",
                    url=item.get("url") or item.get("link") or item.get("source_url", ""),
                    snippet=(
                        item.get("snippet")
                        or item.get("summary")
                        or item.get("text")
                        or ""
                    ),
                    engine="open-evidence",
                    source=item.get("source"),
                    metadata={
                        k: str(v)
                        for k, v in item.items()
                        if k
                        not in {
                            "title",
                            "url",
                            "link",
                            "source_url",
                            "snippet",
                            "summary",
                            "text",
                        }
                    },
                )
            )
        return hits

    @staticmethod
    def _raise_for_status(response: Response) -> None:
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            detail = exc.response.text if exc.response is not None else str(exc)
            raise RuntimeError(f"OpenEvidence API error: {detail}") from exc


@dataclass
class CombinedSearchResult:
    question: str
    augmented_query: str
    perplexity_hits: List[SearchHit]
    open_evidence_hits: List[SearchHit]
    synthesis: Optional[str] = None

    def total_hits(self) -> int:
        return len(self.perplexity_hits) + len(self.open_evidence_hits)


class ClinicalSearchOrchestrator:
    """Runs both APIs and keeps everything focused on trauma-critical care."""

    def __init__(
        self,
        perplexity_client: PerplexityClient,
        open_evidence_client: Optional[OpenEvidenceClient] = None,
    ) -> None:
        self.perplexity = perplexity_client
        self.open_evidence = open_evidence_client

    def run(
        self,
        question: str,
        *,
        max_results: int = 5,
        include_summary: bool = True,
    ) -> CombinedSearchResult:
        normalized_query = self._augment_query(question)

        px_hits = self.perplexity.search(normalized_query, max_results=max_results)

        oe_hits: List[SearchHit] = []
        include_oe = False
        if self.open_evidence and self.open_evidence.is_configured:
            try:
                oe_hits = self.open_evidence.search(
                    normalized_query, max_results=max_results
                )
                include_oe = bool(oe_hits)
            except Exception as exc:
                print(f"[warning] OpenEvidence lookup failed: {exc}")

        synthesis = None
        if include_summary and (px_hits or oe_hits):
            synthesis = self.perplexity.synthesize_answer(
                question,
                list(px_hits) + list(oe_hits),
                include_open_evidence=include_oe,
            )

        return CombinedSearchResult(
            question=question.strip(),
            augmented_query=normalized_query,
            perplexity_hits=px_hits,
            open_evidence_hits=oe_hits,
            synthesis=synthesis,
        )

    @staticmethod
    def _augment_query(question: str) -> str:
        trimmed = question.strip()
        if not trimmed.lower().endswith("trauma"):
            trimmed += " trauma critical care"
        modifiers = (
            "evidence-based guidelines, randomized trials, intensive care outcomes"
        )
        return f"{trimmed} ({modifiers})"


def render_results(result: CombinedSearchResult, *, show_summary: bool = True) -> None:
    print(f"\nClinical question: {result.question}")
    print(f"Augmented query: {result.augmented_query}")

    _render_hit_block("Perplexity", result.perplexity_hits)
    if result.open_evidence_hits:
        _render_hit_block("OpenEvidence", result.open_evidence_hits)
    else:
        print("\n=== OpenEvidence ===")
        print("No OpenEvidence results (check credentials or filters).")

    if show_summary and result.synthesis:
        print("\n=== Synthesized Trauma-Critical Care Summary ===")
        print(textwrap.fill(result.synthesis, width=100))


def _render_hit_block(label: str, hits: List[SearchHit]) -> None:
    print(f"\n=== {label} ({len(hits)} results) ===")
    if not hits:
        print("No results.")
        return

    for idx, hit in enumerate(hits, start=1):
        print(f"[{idx}] {hit.title}")
        if hit.url:
            print(f"    {hit.url}")
        snippet = hit.clipped_snippet()
        if snippet:
            print(
                textwrap.fill(
                    snippet,
                    width=100,
                    initial_indent="    ",
                    subsequent_indent="    ",
                )
            )
        if hit.metadata:
            meta_preview = ", ".join(
                f"{k}={v}" for k, v in list(hit.metadata.items())[:3]
            )
            if meta_preview:
                print(f"    metadata: {meta_preview}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run trauma-focused clinical searches across Perplexity and OpenEvidence."
    )
    parser.add_argument(
        "question",
        nargs="?",
        help="Clinical or research question. Falls back to interactive prompt if omitted.",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=5,
        help="Number of documents to request from each API (default: 5).",
    )
    parser.add_argument(
        "--no-summary",
        action="store_true",
        help="Skip the synthesized summary and just list retrieved evidence.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    question = args.question or input("Enter your clinical or research question: ").strip()
    if not question:
        raise SystemExit("A clinical question is required.")

    perplexity_client = PerplexityClient()
    open_evidence_client = OpenEvidenceClient()

    orchestrator = ClinicalSearchOrchestrator(
        perplexity_client=perplexity_client,
        open_evidence_client=open_evidence_client,
    )
    result = orchestrator.run(
        question,
        max_results=args.max_results,
        include_summary=not args.no_summary,
    )
    render_results(result, show_summary=not args.no_summary)


if __name__ == "__main__":
    main()
