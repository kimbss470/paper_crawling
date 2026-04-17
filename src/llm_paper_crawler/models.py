from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(slots=True)
class Paper:
    title: str
    abstract: str = ""
    authors: list[str] = field(default_factory=list)
    affiliations: list[str] = field(default_factory=list)
    venue: str = ""
    year: int | None = None
    source: str = ""
    status: str = ""
    category: str = ""
    abstract_preview: str = ""
    slug: str = ""
    paper_url: str = ""
    pdf_url: str = ""
    doi: str = ""
    arxiv_id: str = ""
    openreview_forum: str = ""
    keywords: list[str] = field(default_factory=list)
    raw_source_id: str = ""

    def to_dict(self) -> dict:
        return asdict(self)
