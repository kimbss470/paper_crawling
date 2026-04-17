# LLM Paper Crawling

This project crawls LLM-related papers from:

- `arXiv`
- `NeurIPS` proceedings
- `ICML` proceedings
- `ICLR` via `OpenReview`
- `OpenReview` accepted-paper fallback for venues whose accepted papers are public before formal proceedings are available

The crawler normalizes metadata into a single paper schema, filters to LLM-relevant work, deduplicates across sources, exports to `jsonl` or `csv`, and generates a static GitHub Pages site.

The generated site includes:

- `Categorizing`
- `Abstract Preview`
- `At a glance` page with `Title`, `Author`, `Affiliation`, `Conference/Journal Name`, `Year`, and `Category`
- `Per-paper page` with a structured summary based on [summarize_structure.md](/data/kimbss470/LLM/paper_crawling/summarize_structure.md)

## What It Does

The intended flow is:

1. Pull candidate papers from the requested sources.
2. Filter to LLM-related work using a configurable keyword matcher.
3. Deduplicate papers by DOI, arXiv id, OpenReview forum id, or normalized title.
4. When a conference paper is accepted but not yet visible in the main proceedings crawl, keep the `OpenReview` version as a fallback record.

That last rule matters most for venues like `ICLR`, and for periods between acceptance and final proceedings publication.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Crawl Example

```bash
llm-paper-crawl crawl \
  --years 2024 2025 2026 \
  --sources arxiv neurips icml iclr openreview \
  --arxiv-query 'cat:cs.CL OR cat:cs.LG OR cat:cs.AI' \
  --max-arxiv-results 500 \
  --output data/papers.jsonl
```

To export CSV instead:

```bash
llm-paper-crawl crawl \
  --years 2025 \
  --sources neurips icml iclr openreview \
  --output data/papers.csv
```

## Build The Static Site

```bash
llm-paper-crawl build-site \
  --input data/papers.jsonl \
  --site-dir site
```

This produces:

- `site/index.html` for the at-a-glance page
- `site/papers/*.html` for per-paper pages
- `site/data/papers.json` for client-side filtering

## CLI Commands

- `llm-paper-crawl crawl ...`
- `llm-paper-crawl build-site ...`

## Crawl Options

- `--years`: One or more target years.
- `--sources`: Any of `arxiv`, `neurips`, `icml`, `iclr`, `openreview`.
- `--arxiv-query`: Raw arXiv API query string.
- `--max-arxiv-results`: Max arXiv records to fetch.
- `--openreview-username`: Optional. Not required for public OpenReview papers.
- `--openreview-password`: Optional. Not required for public OpenReview papers.
- `--output`: Output file path ending in `.jsonl` or `.csv`.
- `--include-non-llm`: Keep everything instead of applying the LLM keyword filter.

## Site Build Options

- `--input`: Input `.jsonl` file from the crawl step.
- `--site-dir`: Output directory for the generated Pages site.

## Data Model

Each paper is normalized into fields like:

- `title`
- `abstract`
- `abstract_preview`
- `authors`
- `affiliations`
- `venue`
- `year`
- `category`
- `slug`
- `source`
- `status`
- `pdf_url`
- `paper_url`
- `doi`
- `arxiv_id`
- `openreview_forum`
- `keywords`

## Notes on Coverage

- `arXiv` is queried through the public export API.
- `NeurIPS` is scraped from the official proceedings pages.
- `ICML` is scraped from the official `Proceedings of Machine Learning Research` site.
- `ICLR` is collected from `OpenReview`, which is also used as the fallback source for accepted-but-not-yet-published papers.
- `OpenReview` access defaults to public-only crawling. No OpenReview login is required for open papers.

Official sources change their HTML over time, so the conference scrapers are intentionally isolated by source and easy to patch.

## OpenReview Fallback Logic

`OpenReview` records are marked as:

- `accepted_openreview` when they represent an accepted paper
- `published` when they come from a proceedings source

If a published proceedings record and an accepted OpenReview record resolve to the same paper, the proceedings record wins and the OpenReview duplicate is dropped.

## GitHub Pages Deployment

The workflow at [.github/workflows/pages.yml](/data/kimbss470/LLM/paper_crawling/.github/workflows/pages.yml) runs the crawl, builds the static site, and deploys it to GitHub Pages.

One-time GitHub setup:

1. Push the repository to GitHub.
2. In repository settings, set `Pages` source to `GitHub Actions`.
3. No OpenReview secrets are required for public papers.
4. Only add `OPENREVIEW_USERNAME` and `OPENREVIEW_PASSWORD` if you later decide to crawl non-public OpenReview content.

I do not need `gh login` to finish local code changes. I only need GitHub access if you want me to push the repo, create the repository, or inspect Actions runs for you.

## Project Layout

```text
src/llm_paper_crawler/
  cli.py
  export.py
  filters.py
  models.py
  pipeline.py
  site.py
  summarizer.py
  sources/
    arxiv.py
    openreview.py
    proceedings.py
```
