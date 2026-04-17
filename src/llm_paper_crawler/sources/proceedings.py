from __future__ import annotations

import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from ..models import Paper
from .base import BaseCrawler
from .openreview import ICLRCrawler as OpenReviewICLRCrawler


USER_AGENT = "llm-paper-crawling/0.1 (+https://example.local)"


class NeurIPSCrawler(BaseCrawler):
    def __init__(self, session: requests.Session | None = None) -> None:
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    def fetch_many(self, years: list[int]) -> list[Paper]:
        papers: list[Paper] = []
        for year in years:
            url = f"https://proceedings.neurips.cc/paper_files/paper/{year}"
            try:
                response = self.session.get(url, timeout=60)
                response.raise_for_status()
            except Exception:
                continue

            soup = BeautifulSoup(response.text, "html.parser")
            for anchor in soup.select("ul li a"):
                href = anchor.get("href", "")
                title = " ".join(anchor.get_text(" ", strip=True).split())
                if not href or not title:
                    continue
                if "/hash/" not in href:
                    continue
                detail_url = urljoin(url + "/", href)
                papers.append(_fetch_neurips_detail(self.session, detail_url, year, title))
        return [paper for paper in papers if paper is not None]


class ICMLCrawler(BaseCrawler):
    def __init__(self, session: requests.Session | None = None) -> None:
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    def fetch_many(self, years: list[int]) -> list[Paper]:
        papers: list[Paper] = []
        for year in years:
            volume_url = _find_icml_volume_url(self.session, year)
            if not volume_url:
                continue

            response = self.session.get(volume_url, timeout=60)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            for anchor in soup.select("div.paper a[href$='.html'], p.links a[href$='.html']"):
                href = anchor.get("href", "")
                if not href:
                    continue
                detail_url = urljoin(volume_url, href)
                paper = _fetch_icml_detail(self.session, detail_url, year)
                if paper is not None:
                    papers.append(paper)
        return papers


class ICLRCrawlerProxy(BaseCrawler):
    def __init__(self, username: str = "", password: str = "") -> None:
        self.delegate = OpenReviewICLRCrawler(username=username, password=password)

    def fetch_many(self, years: list[int]) -> list[Paper]:
        return self.delegate.fetch_many(years)


class ICLRCrawler(ICLRCrawlerProxy):
    pass


def _fetch_neurips_detail(session: requests.Session, detail_url: str, year: int, fallback_title: str) -> Paper | None:
    try:
        response = session.get(detail_url, timeout=60)
        response.raise_for_status()
    except Exception:
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    title = _first_text(soup.select("h4")) or fallback_title
    authors = [_normalize_text(anchor.get_text(" ", strip=True)) for anchor in soup.select("i + a")]
    affiliations = _extract_affiliations(soup)
    pdf_anchor = soup.find("a", string=re.compile(r"Paper|PDF", re.IGNORECASE))
    abstract = _extract_abstract_block(soup)

    return Paper(
        title=title,
        abstract=abstract,
        authors=[author for author in authors if author],
        affiliations=affiliations,
        venue=f"NeurIPS {year}",
        year=year,
        source="neurips",
        status="published",
        paper_url=detail_url,
        pdf_url=urljoin(detail_url, pdf_anchor.get("href")) if pdf_anchor else "",
        raw_source_id=detail_url,
    )


def _find_icml_volume_url(session: requests.Session, year: int) -> str:
    index_url = "https://proceedings.mlr.press/"
    response = session.get(index_url, timeout=60)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    for anchor in soup.select("a[href]"):
        text = anchor.get_text(" ", strip=True)
        href = anchor.get("href", "")
        if "International Conference on Machine Learning" in text and str(year) in text:
            return urljoin(index_url, href)
    return ""


def _fetch_icml_detail(session: requests.Session, detail_url: str, year: int) -> Paper | None:
    try:
        response = session.get(detail_url, timeout=60)
        response.raise_for_status()
    except Exception:
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    title = _first_text(soup.select("h1")) or _first_text(soup.select("title"))
    if not title:
        return None

    authors = [_normalize_text(item.get_text(" ", strip=True)) for item in soup.select("span.authors, #authors")]
    if not authors:
        authors = [_normalize_text(item) for item in re.split(r",| and ", _first_text(soup.select("meta[name='citation_author']")))]

    affiliations = _extract_affiliations(soup)
    abstract = _extract_meta_content(soup, "description")
    pdf_url = _meta_or_link_pdf(soup, detail_url)
    doi = _extract_meta_content(soup, "citation_doi")

    return Paper(
        title=_normalize_text(title),
        abstract=abstract,
        authors=[author for author in authors if author],
        affiliations=affiliations,
        venue=f"ICML {year}",
        year=year,
        source="icml",
        status="published",
        paper_url=detail_url,
        pdf_url=pdf_url,
        doi=doi,
        raw_source_id=detail_url,
    )


def _extract_abstract_block(soup: BeautifulSoup) -> str:
    meta_abstract = _extract_meta_content(soup, "description")
    if meta_abstract:
        return meta_abstract
    candidates = soup.find_all(string=re.compile(r"abstract", re.IGNORECASE))
    for candidate in candidates:
        parent = candidate.parent
        if parent and parent.parent:
            text = parent.parent.get_text(" ", strip=True)
            if len(text) > len(candidate) + 20:
                return _normalize_text(text)
    return ""


def _meta_or_link_pdf(soup: BeautifulSoup, base_url: str) -> str:
    for name in ("citation_pdf_url",):
        value = _extract_meta_content(soup, name)
        if value:
            return value
    for anchor in soup.select("a[href$='.pdf']"):
        return urljoin(base_url, anchor.get("href", ""))
    return ""


def _extract_meta_content(soup: BeautifulSoup, name: str) -> str:
    tag = soup.find("meta", attrs={"name": name})
    if tag and tag.get("content"):
        return _normalize_text(tag["content"])
    return ""


def _extract_meta_contents(soup: BeautifulSoup, name: str) -> list[str]:
    values: list[str] = []
    for tag in soup.find_all("meta", attrs={"name": name}):
        content = tag.get("content", "")
        if content:
            normalized = _normalize_text(content)
            if normalized and normalized not in values:
                values.append(normalized)
    return values


def _extract_affiliations(soup: BeautifulSoup) -> list[str]:
    affiliations = _extract_meta_contents(soup, "citation_author_institution")
    if affiliations:
        return affiliations

    selectors = [
        ".authors .affiliation",
        ".authors .institution",
        ".affiliations",
        "#affiliations",
    ]
    for selector in selectors:
        values = [_normalize_text(node.get_text(" ", strip=True)) for node in soup.select(selector)]
        values = [value for value in values if value]
        if values:
            return _dedupe(values)

    return []


def _first_text(nodes) -> str:
    for node in nodes:
        text = node.get_text(" ", strip=True)
        if text:
            return _normalize_text(text)
    return ""


def _normalize_text(text: str) -> str:
    return " ".join(text.split())


def _dedupe(values: list[str]) -> list[str]:
    deduped: list[str] = []
    for value in values:
        if value and value not in deduped:
            deduped.append(value)
    return deduped
