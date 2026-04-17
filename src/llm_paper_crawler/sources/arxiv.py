from __future__ import annotations

import xml.etree.ElementTree as ET
from urllib.parse import urlencode

import requests

from ..models import Paper
from .base import BaseCrawler


ARXIV_API_URL = "https://export.arxiv.org/api/query"
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


class ArxivCrawler(BaseCrawler):
    def __init__(self, search_query: str, max_results: int = 250, session: requests.Session | None = None) -> None:
        self.search_query = search_query
        self.max_results = max_results
        self.session = session or requests.Session()

    def fetch_many(self, years: list[int]) -> list[Paper]:
        del years
        params = {
            "search_query": self.search_query,
            "start": 0,
            "max_results": self.max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
        response = self.session.get(f"{ARXIV_API_URL}?{urlencode(params)}", timeout=60)
        response.raise_for_status()

        root = ET.fromstring(response.text)
        papers: list[Paper] = []
        for entry in root.findall("atom:entry", ATOM_NS):
            entry_id = _text(entry, "atom:id")
            arxiv_id = entry_id.rstrip("/").split("/")[-1]
            published = _text(entry, "atom:published")
            year = int(published[:4]) if published else None
            author_nodes = entry.findall("atom:author", ATOM_NS)

            papers.append(
                Paper(
                    title=_text(entry, "atom:title"),
                    abstract=_text(entry, "atom:summary"),
                    authors=[author.findtext("{http://www.w3.org/2005/Atom}name", default="").strip() for author in author_nodes],
                    affiliations=_extract_affiliations(author_nodes),
                    venue="arXiv",
                    year=year,
                    source="arxiv",
                    status="preprint",
                    paper_url=entry_id,
                    pdf_url=_find_pdf_url(entry),
                    doi=_arxiv_doi(entry),
                    arxiv_id=arxiv_id,
                    raw_source_id=entry_id,
                )
            )
        return papers


def _find_pdf_url(entry: ET.Element) -> str:
    for link in entry.findall("atom:link", ATOM_NS):
        if link.attrib.get("title") == "pdf":
            return link.attrib.get("href", "")
    return ""


def _arxiv_doi(entry: ET.Element) -> str:
    doi = entry.find("{http://arxiv.org/schemas/atom}doi")
    return doi.text.strip() if doi is not None and doi.text else ""


def _text(entry: ET.Element, path: str) -> str:
    text = entry.findtext(path, default="", namespaces=ATOM_NS)
    return " ".join(text.split())


def _extract_affiliations(author_nodes: list[ET.Element]) -> list[str]:
    affiliations: list[str] = []
    for author in author_nodes:
        for child in author:
            tag = child.tag.rsplit("}", 1)[-1]
            if tag == "affiliation" and child.text:
                value = " ".join(child.text.split())
                if value and value not in affiliations:
                    affiliations.append(value)
    return affiliations
