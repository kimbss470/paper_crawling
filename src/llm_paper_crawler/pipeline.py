from __future__ import annotations

from .filters import categorize_paper, extract_keyword_hits, is_llm_related, normalize_title
from .models import Paper


def enrich_and_filter(papers: list[Paper], include_non_llm: bool = False) -> list[Paper]:
    enriched: list[Paper] = []
    for paper in papers:
        if not paper.keywords:
            paper.keywords = extract_keyword_hits(f"{paper.title}\n{paper.abstract}\n{paper.venue}")
        if not paper.category:
            paper.category = categorize_paper(f"{paper.title}\n{paper.abstract}\n{paper.venue}\n{' '.join(paper.keywords)}")
        if not paper.abstract_preview:
            paper.abstract_preview = build_abstract_preview(paper.abstract)
        if not paper.slug:
            paper.slug = build_slug(paper)
        if include_non_llm or is_llm_related(paper):
            enriched.append(paper)
    return enriched


def deduplicate_papers(papers: list[Paper]) -> list[Paper]:
    chosen: dict[str, Paper] = {}

    for paper in papers:
        candidate_keys = _dedupe_keys(paper)
        existing_key = next((key for key in candidate_keys if key in chosen), None)
        if existing_key is None:
            chosen[candidate_keys[0]] = paper
            continue

        selected = _prefer(chosen[existing_key], paper)
        for key in candidate_keys:
            chosen[key] = selected

    unique_by_identity: dict[int, Paper] = {}
    for paper in chosen.values():
        unique_by_identity[id(paper)] = paper
    return sorted(unique_by_identity.values(), key=lambda item: ((item.year or 0), item.venue, item.title))


def _dedupe_keys(paper: Paper) -> list[str]:
    keys: list[str] = []
    if paper.doi:
        keys.append(f"doi:{paper.doi.lower()}")
    if paper.arxiv_id:
        keys.append(f"arxiv:{paper.arxiv_id.lower()}")
    if paper.openreview_forum:
        keys.append(f"openreview:{paper.openreview_forum}")
    keys.append(f"title:{normalize_title(paper.title)}")
    return keys


def _prefer(left: Paper, right: Paper) -> Paper:
    score_left = _paper_priority(left)
    score_right = _paper_priority(right)
    return left if score_left >= score_right else right


def _paper_priority(paper: Paper) -> tuple[int, int, int]:
    status_rank = {
        "published": 3,
        "accepted_openreview": 2,
        "preprint": 1,
    }.get(paper.status, 0)
    metadata_rank = sum(bool(value) for value in [paper.abstract, paper.pdf_url, paper.paper_url, paper.doi])
    return (status_rank, metadata_rank, len(paper.authors))


def build_slug(paper: Paper) -> str:
    base = normalize_title(paper.title)[:72] or "paper"
    suffix = str(paper.year or "unknown")
    return f"{base}-{suffix}"


def build_abstract_preview(abstract: str, limit: int = 260) -> str:
    cleaned = " ".join(abstract.split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "..."
