from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

from .models import Paper


DEFAULT_LLM_KEYWORDS = [
    "large language model",
    "large language models",
    "llm",
    "foundation model",
    "foundation models",
    "language model",
    "language models",
    "generative ai",
    "instruction tuning",
    "instruction-tuning",
    "alignment",
    "pretraining",
    "pre-training",
    "reasoning",
    "agent",
    "agents",
    "retrieval-augmented generation",
    "rag",
    "prompting",
    "chain-of-thought",
    "transformer",
]

CATEGORY_KEYWORDS = {
    "Reasoning": ["reasoning", "chain-of-thought", "verifier", "deliberation", "planning"],
    "Agents": ["agent", "agents", "tool use", "tool-use", "web agent", "workflow"],
    "Retrieval": ["retrieval", "rag", "knowledge base", "search", "grounding"],
    "Alignment": ["alignment", "preference", "rlhf", "safety", "constitutional"],
    "Efficiency": ["quantization", "distillation", "compression", "pruning", "efficient", "latency"],
    "Multimodal": ["vision-language", "multimodal", "image", "audio", "video", "speech"],
    "Benchmarks": ["benchmark", "evaluation", "leaderboard", "dataset", "arena"],
    "Training": ["pretraining", "pre-training", "instruction tuning", "fine-tuning", "sft"],
}


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    value = re.sub(r"\s+", " ", value).strip()
    return value


def normalize_title(value: str) -> str:
    value = normalize_text(value)
    return re.sub(r"[^a-z0-9]+", "", value)


def extract_keyword_hits(text: str, keywords: Iterable[str] = DEFAULT_LLM_KEYWORDS) -> list[str]:
    haystack = normalize_text(text)
    return [keyword for keyword in keywords if keyword in haystack]


def is_llm_related(paper: Paper, keywords: Iterable[str] = DEFAULT_LLM_KEYWORDS) -> bool:
    combined = " ".join([paper.title, paper.abstract, paper.venue, *paper.keywords])
    return bool(extract_keyword_hits(combined, keywords))


def categorize_paper(text: str) -> str:
    haystack = normalize_text(text)
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in haystack for keyword in keywords):
            return category
    return "General LLM"
