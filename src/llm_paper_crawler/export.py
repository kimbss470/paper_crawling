from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .models import Paper


def export_papers(papers: list[Paper], output_path: str) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.suffix == ".jsonl":
        with path.open("w", encoding="utf-8") as handle:
            for paper in papers:
                handle.write(json.dumps(paper.to_dict(), ensure_ascii=False) + "\n")
        return

    if path.suffix == ".csv":
        rows = [_paper_to_csv_row(paper) for paper in papers]
        fieldnames = list(rows[0].keys()) if rows else _paper_to_csv_row(Paper(title="")).keys()
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        return

    raise ValueError(f"Unsupported output format for {output_path!r}. Use .jsonl or .csv")


def _paper_to_csv_row(paper: Paper) -> dict[str, Any]:
    data = paper.to_dict()
    data["authors"] = "; ".join(paper.authors)
    data["keywords"] = "; ".join(paper.keywords)
    return data
