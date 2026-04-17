from __future__ import annotations

import html
import re

from .models import Paper


SECTION_ORDER = [
    "Summary",
    "Motivation",
    "Key Idea",
    "Experimental Results",
    "Data analysis",
    "Discussion (e.g., future work)",
    "Significance of this study",
    "Useful references to consider",
]


def build_summary_sections(paper: Paper) -> dict[str, list[str]]:
    sentences = split_sentences(paper.abstract)
    summary = [
        f"Presented in **{escape_markdown(paper.venue or paper.source)}** ({paper.year or 'year unknown'}).",
        f"Category: **{escape_markdown(paper.category or 'General LLM')}**.",
    ]
    if sentences:
        summary.append(sentences[0])

    motivation = _pick_sentences(
        sentences,
        ["motivate", "challenge", "problem", "limit", "bottleneck", "need", "require"],
        fallback="The crawled metadata does not explicitly separate the motivation; infer it from the abstract preview.",
    )
    key_idea = _pick_sentences(
        sentences,
        ["propose", "introduce", "present", "develop", "method", "framework", "approach"],
        fallback="The key idea should be derived from the title and abstract because no full-text summary is available yet.",
    )
    experiments = _pick_sentences(
        sentences,
        ["experiment", "result", "benchmark", "evaluate", "outperform", "improve", "accuracy"],
        fallback="Experimental details are not explicit in the available metadata.",
    )
    data_analysis = _pick_sentences(
        sentences,
        ["dataset", "data", "analysis", "ablation", "corpus", "sample"],
        fallback="Dataset and analysis details were not clearly available from the crawled abstract.",
    )
    discussion = _pick_sentences(
        sentences,
        ["future work", "limitation", "discussion", "however", "although"],
        fallback="Future work and limitations are not explicit in the current metadata view.",
    )
    significance = [
        f"This paper appears relevant to **{escape_markdown(paper.category or 'LLM research')}** tracking.",
        "A full-paper summarization pass can refine this section once PDF parsing or LLM summarization is added.",
    ]

    references = []
    if paper.paper_url:
        references.append(f"[Paper page]({paper.paper_url})")
    if paper.pdf_url:
        references.append(f"[PDF]({paper.pdf_url})")
    if not references:
        references.append("No external references were extracted beyond the crawled metadata.")

    return {
        "Summary": summary,
        "Motivation": motivation,
        "Key Idea": key_idea,
        "Experimental Results": experiments,
        "Data analysis": data_analysis,
        "Discussion (e.g., future work)": discussion,
        "Significance of this study": significance,
        "Useful references to consider": references,
    }


def render_summary_markdown(paper: Paper) -> str:
    sections = build_summary_sections(paper)
    lines = [f"# **{escape_markdown(paper.title)}**"]
    for section in SECTION_ORDER:
        lines.append(f"## **{section}**")
        lines.extend(f"- {item}" for item in sections[section])
    return "\n".join(lines)


def split_sentences(text: str) -> list[str]:
    cleaned = " ".join(text.split())
    if not cleaned:
        return []
    parts = re.split(r"(?<=[.!?])\s+", cleaned)
    return [part.strip() for part in parts if part.strip()]


def escape_markdown(value: str) -> str:
    return html.escape(value, quote=False)


def _pick_sentences(sentences: list[str], keywords: list[str], fallback: str) -> list[str]:
    matched = [sentence for sentence in sentences if any(keyword in sentence.lower() for keyword in keywords)]
    if matched:
        return matched[:3]
    if sentences:
        return sentences[:2]
    return [fallback]
