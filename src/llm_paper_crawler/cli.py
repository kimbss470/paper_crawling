from __future__ import annotations

import argparse
import os

from .export import export_papers
from .pipeline import deduplicate_papers, enrich_and_filter
from .site import build_site
from .sources.arxiv import ArxivCrawler
from .sources.openreview import OpenReviewCrawler
from .sources.proceedings import ICMLCrawler, ICLRCrawler, NeurIPSCrawler


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Crawl LLM-related papers and build a GitHub Pages site.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    crawl = subparsers.add_parser("crawl", help="Run crawlers and export normalized paper metadata.")
    crawl.add_argument("--years", nargs="+", type=int, required=True, help="Target publication or conference years.")
    crawl.add_argument(
        "--sources",
        nargs="+",
        choices=["arxiv", "neurips", "icml", "iclr", "openreview"],
        required=True,
        help="Sources to crawl.",
    )
    crawl.add_argument(
        "--arxiv-query",
        default="cat:cs.CL OR cat:cs.LG OR cat:cs.AI",
        help="Raw arXiv API search query.",
    )
    crawl.add_argument("--max-arxiv-results", type=int, default=250)
    crawl.add_argument("--openreview-username", default=os.getenv("OPENREVIEW_USERNAME", ""))
    crawl.add_argument("--openreview-password", default=os.getenv("OPENREVIEW_PASSWORD", ""))
    crawl.add_argument("--include-non-llm", action="store_true")
    crawl.add_argument("--output", required=True, help="Output path ending with .jsonl or .csv")

    build = subparsers.add_parser("build-site", help="Generate the static site from a JSONL export.")
    build.add_argument("--input", required=True, help="Input JSONL file produced by the crawl command.")
    build.add_argument("--site-dir", default="site", help="Output directory for the generated site.")

    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "build-site":
        build_site(input_path=args.input, site_dir=args.site_dir)
        return

    crawlers = []

    if "arxiv" in args.sources:
        crawlers.append(ArxivCrawler(search_query=args.arxiv_query, max_results=args.max_arxiv_results))
    if "neurips" in args.sources:
        crawlers.append(NeurIPSCrawler())
    if "icml" in args.sources:
        crawlers.append(ICMLCrawler())
    if "iclr" in args.sources:
        crawlers.append(ICLRCrawler(args.openreview_username, args.openreview_password))
    if "openreview" in args.sources:
        crawlers.append(OpenReviewCrawler(args.openreview_username, args.openreview_password))

    papers = []
    for crawler in crawlers:
        papers.extend(crawler.fetch_many(args.years))

    filtered = enrich_and_filter(papers, include_non_llm=args.include_non_llm)
    deduped = deduplicate_papers(filtered)
    export_papers(deduped, args.output)


if __name__ == "__main__":
    main()
