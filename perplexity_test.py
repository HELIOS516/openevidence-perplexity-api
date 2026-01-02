from __future__ import annotations

import os

from dotenv import load_dotenv
from perplexity import Perplexity


def main() -> None:
    load_dotenv()
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        raise SystemExit("PERPLEXITY_API_KEY is missing. Add it to your environment or .env file.")

    client = Perplexity(api_key=api_key)
    search = client.search.create(
        query="medical AI guidelines 2024 trauma critical care",
        max_results=5,
        search_mode="web",
    )
    for idx, result in enumerate(search.results, start=1):
        print(f"[{idx}] {result.title}: {result.url}")


if __name__ == "__main__":
    main()
