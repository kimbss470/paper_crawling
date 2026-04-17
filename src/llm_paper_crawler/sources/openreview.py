from __future__ import annotations

from dataclasses import dataclass

try:
    import openreview
except ImportError:  # pragma: no cover - handled at runtime
    openreview = None

from ..models import Paper
from .base import BaseCrawler


DEFAULT_OPENREVIEW_VENUES = {
    "iclr": "ICLR.cc/{year}/Conference",
    "icml": "ICML.cc/{year}/Conference",
    "neurips": "NeurIPS.cc/{year}/Conference",
}


@dataclass(slots=True)
class OpenReviewCrawler(BaseCrawler):
    username: str = ""
    password: str = ""
    venues: tuple[str, ...] = ("iclr", "icml", "neurips")

    def fetch_many(self, years: list[int]) -> list[Paper]:
        client = self._build_client()
        papers: list[Paper] = []
        for venue_key in self.venues:
            template = DEFAULT_OPENREVIEW_VENUES[venue_key]
            for year in years:
                venue_id = template.format(year=year)
                try:
                    papers.extend(self._fetch_accepted(client, venue_id, venue_name=venue_key.upper(), year=year))
                except Exception:
                    continue
        return papers

    def _build_client(self):
        if openreview is None:
            raise RuntimeError("openreview-py is not installed. Run `pip install -e .` first.")

        kwargs = {"baseurl": "https://api2.openreview.net"}
        if self.username and self.password:
            kwargs["username"] = self.username
            kwargs["password"] = self.password
        return openreview.api.OpenReviewClient(**kwargs)

    def _fetch_accepted(self, client, venue_id: str, venue_name: str, year: int) -> list[Paper]:
        notes = client.get_all_notes(content={"venueid": venue_id})
        papers: list[Paper] = []
        for note in notes:
            content = _note_content(note)
            title = _content_value(content, "title")
            if not title:
                continue

            abstract = _content_value(content, "abstract")
            pdf_path = _content_value(content, "pdf")
            forum = getattr(note, "forum", "") or getattr(note, "id", "")
            pdf_url = _make_openreview_pdf_url(pdf_path, forum)

            papers.append(
                Paper(
                    title=title,
                    abstract=abstract,
                    authors=_content_list(content, "authors"),
                    affiliations=_content_affiliations(content),
                    venue=f"{venue_name} {year}",
                    year=year,
                    source="openreview",
                    status="accepted_openreview",
                    paper_url=f"https://openreview.net/forum?id={forum}" if forum else "",
                    pdf_url=pdf_url,
                    openreview_forum=forum,
                    raw_source_id=getattr(note, "id", forum),
                )
            )
        return papers


class ICLRCrawler(OpenReviewCrawler):
    def __init__(self, username: str = "", password: str = "") -> None:
        super().__init__(username=username, password=password, venues=("iclr",))


def _note_content(note) -> dict:
    content = getattr(note, "content", {})
    return content if isinstance(content, dict) else {}


def _content_value(content: dict, key: str) -> str:
    value = content.get(key, "")
    if isinstance(value, dict):
        value = value.get("value", "")
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value).strip()


def _content_list(content: dict, key: str) -> list[str]:
    value = content.get(key, [])
    if isinstance(value, dict):
        value = value.get("value", [])
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if value:
        return [str(value).strip()]
    return []


def _content_affiliations(content: dict) -> list[str]:
    affiliations: list[str] = []
    candidate_keys = ("affiliations", "institution", "institutions")
    for key in candidate_keys:
        affiliations.extend(_content_list(content, key))

    authors_value = content.get("authors", [])
    if isinstance(authors_value, dict):
        authors_value = authors_value.get("value", [])
    if isinstance(authors_value, list):
        for item in authors_value:
            if isinstance(item, dict):
                for nested_key in ("affiliation", "institution"):
                    nested_value = item.get(nested_key)
                    if nested_value:
                        text = str(nested_value).strip()
                        if text and text not in affiliations:
                            affiliations.append(text)

    author_info = content.get("author_info", {})
    if isinstance(author_info, dict):
        for nested_key in ("affiliations", "institutions"):
            nested_value = author_info.get(nested_key)
            if isinstance(nested_value, list):
                for item in nested_value:
                    text = str(item).strip()
                    if text and text not in affiliations:
                        affiliations.append(text)

    deduped: list[str] = []
    for affiliation in affiliations:
        if affiliation and affiliation not in deduped:
            deduped.append(affiliation)
    return deduped


def _make_openreview_pdf_url(pdf_path: str, forum: str) -> str:
    if pdf_path.startswith("http://") or pdf_path.startswith("https://"):
        return pdf_path
    if pdf_path:
        return f"https://openreview.net{pdf_path}"
    if forum:
        return f"https://openreview.net/pdf?id={forum}"
    return ""
