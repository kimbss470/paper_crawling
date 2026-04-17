from __future__ import annotations

import json
from pathlib import Path

from .models import Paper
from .summarizer import SECTION_ORDER, build_summary_sections


def build_site(input_path: str, site_dir: str = "site") -> None:
    papers = [Paper(**row) for row in _load_jsonl(input_path)]
    target = Path(site_dir)
    _ensure_dirs(target)
    _write_assets(target)
    _write_index(target, papers)
    _write_paper_pages(target, papers)
    _write_data(target, papers)


def _load_jsonl(path: str) -> list[dict]:
    rows = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                rows.append(json.loads(stripped))
    return rows


def _ensure_dirs(target: Path) -> None:
    (target / "assets").mkdir(parents=True, exist_ok=True)
    (target / "papers").mkdir(parents=True, exist_ok=True)
    (target / "data").mkdir(parents=True, exist_ok=True)


def _write_assets(target: Path) -> None:
    (target / "assets" / "styles.css").write_text(STYLES_CSS, encoding="utf-8")
    (target / "assets" / "app.js").write_text(APP_JS, encoding="utf-8")


def _write_index(target: Path, papers: list[Paper]) -> None:
    cards = "\n".join(_render_card(paper) for paper in sorted(papers, key=lambda item: ((item.year or 0), item.title), reverse=True))
    html = INDEX_HTML.replace("{{ cards }}", cards)
    (target / "index.html").write_text(html, encoding="utf-8")


def _write_paper_pages(target: Path, papers: list[Paper]) -> None:
    for paper in papers:
        sections = build_summary_sections(paper)
        blocks = []
        for section in SECTION_ORDER:
            items = "".join(f"<li>{item}</li>" for item in sections[section])
            blocks.append(f"<section><h2>{section}</h2><ul>{items}</ul></section>")

        affiliations = ", ".join(paper.affiliations) if paper.affiliations else "Not available from crawled metadata"
        page = PAPER_HTML_TEMPLATE
        page = page.replace("{{ title }}", _escape(paper.title))
        page = page.replace("{{ venue }}", _escape(paper.venue or paper.source))
        page = page.replace("{{ year }}", str(paper.year or "Unknown"))
        page = page.replace("{{ category }}", _escape(paper.category or "General LLM"))
        page = page.replace("{{ authors }}", _escape(", ".join(paper.authors) or "Unknown"))
        page = page.replace("{{ affiliations }}", _escape(affiliations))
        page = page.replace("{{ abstract_preview }}", _escape(paper.abstract_preview or paper.abstract or "No abstract available."))
        page = page.replace("{{ paper_url }}", paper.paper_url or "#")
        page = page.replace("{{ pdf_url }}", paper.pdf_url or "#")
        page = page.replace("{{ summary_blocks }}", "\n".join(blocks))
        (target / "papers" / f"{paper.slug}.html").write_text(page, encoding="utf-8")


def _write_data(target: Path, papers: list[Paper]) -> None:
    payload = {
        "summary": {
            "total_papers": len(papers),
            "total_categories": len({paper.category for paper in papers if paper.category}),
            "total_venues": len({paper.venue for paper in papers if paper.venue}),
        },
        "papers": [paper.to_dict() for paper in papers],
    }
    (target / "data" / "papers.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _render_card(paper: Paper) -> str:
    affiliations = ", ".join(paper.affiliations) if paper.affiliations else "Not available"
    return f"""
    <article class="paper-card" data-year="{paper.year or ''}" data-category="{_escape(paper.category)}" data-venue="{_escape(paper.venue)}">
      <div class="paper-meta">
        <span class="pill">{_escape(paper.category or 'General LLM')}</span>
        <span class="pill subtle">{_escape(paper.venue or paper.source)}</span>
      </div>
      <h2><a href="./papers/{paper.slug}.html">{_escape(paper.title)}</a></h2>
      <p class="at-a-glance"><strong>Authors:</strong> {_escape(', '.join(paper.authors) or 'Unknown')}</p>
      <p class="at-a-glance"><strong>Affiliation:</strong> {_escape(affiliations)}</p>
      <p class="at-a-glance"><strong>Year:</strong> {paper.year or 'Unknown'}</p>
      <p class="preview">{_escape(paper.abstract_preview or paper.abstract or 'No abstract available.')}</p>
    </article>
    """


def _escape(value: str) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


INDEX_HTML = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>LLM Paper Browser</title>
    <link rel="stylesheet" href="./assets/styles.css">
  </head>
  <body>
    <main class="shell">
      <header class="hero">
        <p class="eyebrow">LLM Paper Browser</p>
        <h1>At a glance: title, author, affiliation, venue, year, category.</h1>
        <p class="lede">
          Browse categorized papers, skim abstract previews, and open per-paper pages with structured summaries based on your template.
        </p>
        <div class="toolbar">
          <input id="searchInput" type="search" placeholder="Search title, author, abstract, category">
          <select id="categoryFilter">
            <option value="">All categories</option>
          </select>
        </div>
      </header>
      <section id="paperGrid" class="paper-grid">
        {{ cards }}
      </section>
    </main>
    <script src="./assets/app.js"></script>
  </body>
</html>
"""


PAPER_HTML_TEMPLATE = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{{ title }}</title>
    <link rel="stylesheet" href="../assets/styles.css">
  </head>
  <body>
    <main class="shell paper-shell">
      <p><a class="back-link" href="../index.html">Back to at-a-glance view</a></p>
      <header class="hero paper-hero">
        <p class="eyebrow">{{ category }}</p>
        <h1>{{ title }}</h1>
        <div class="detail-grid">
          <p><strong>Authors</strong><br>{{ authors }}</p>
          <p><strong>Affiliations</strong><br>{{ affiliations }}</p>
          <p><strong>Venue</strong><br>{{ venue }}</p>
          <p><strong>Year</strong><br>{{ year }}</p>
        </div>
        <p class="lede"><strong>Abstract preview:</strong> {{ abstract_preview }}</p>
        <p class="link-row">
          <a href="{{ paper_url }}" target="_blank" rel="noreferrer">Paper page</a>
          <a href="{{ pdf_url }}" target="_blank" rel="noreferrer">PDF</a>
        </p>
      </header>
      <article class="summary-article">
        {{ summary_blocks }}
      </article>
    </main>
  </body>
</html>
"""


APP_JS = """const searchInput = document.getElementById("searchInput");
const categoryFilter = document.getElementById("categoryFilter");
const cards = [...document.querySelectorAll(".paper-card")];

const categories = [...new Set(cards.map(card => card.dataset.category).filter(Boolean))].sort((a, b) => a.localeCompare(b));
for (const category of categories) {
  const option = document.createElement("option");
  option.value = category;
  option.textContent = category;
  categoryFilter.appendChild(option);
}

function applyFilters() {
  const query = (searchInput.value || "").trim().toLowerCase();
  const category = categoryFilter.value;
  for (const card of cards) {
    const text = card.textContent.toLowerCase();
    const matchesQuery = !query || text.includes(query);
    const matchesCategory = !category || card.dataset.category === category;
    card.hidden = !(matchesQuery && matchesCategory);
  }
}

searchInput?.addEventListener("input", applyFilters);
categoryFilter?.addEventListener("change", applyFilters);
"""


STYLES_CSS = """:root {
  --bg: #f4efe8;
  --panel: rgba(255, 251, 245, 0.88);
  --text: #221b17;
  --muted: #665f59;
  --accent: #0d6c63;
  --accent-soft: #d6efe9;
  --line: rgba(34, 27, 23, 0.12);
  --shadow: 0 18px 42px rgba(52, 38, 28, 0.08);
}

* { box-sizing: border-box; }
body {
  margin: 0;
  color: var(--text);
  background:
    radial-gradient(circle at top left, rgba(13, 108, 99, 0.12), transparent 24%),
    radial-gradient(circle at 85% 10%, rgba(193, 141, 74, 0.12), transparent 22%),
    linear-gradient(180deg, #ece6dc 0%, var(--bg) 42%, #f7f4ef 100%);
  font-family: Georgia, "Times New Roman", serif;
}
.shell {
  width: min(1180px, calc(100vw - 28px));
  margin: 0 auto;
  padding: 32px 0 72px;
}
.hero,
.paper-card,
.summary-article section {
  border: 1px solid var(--line);
  background: var(--panel);
  box-shadow: var(--shadow);
}
.hero {
  padding: 28px;
  border-radius: 28px;
}
.eyebrow {
  margin: 0 0 10px;
  color: var(--accent);
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font: 700 12px/1.2 Arial, sans-serif;
}
.hero h1 {
  margin: 0;
  font-size: clamp(2.2rem, 6vw, 4.8rem);
  line-height: 0.95;
  letter-spacing: -0.05em;
  max-width: 12ch;
}
.lede {
  max-width: 72ch;
  line-height: 1.7;
  color: var(--muted);
}
.toolbar {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 12px;
  margin-top: 22px;
}
.toolbar input,
.toolbar select {
  width: 100%;
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 14px 16px;
  background: rgba(255, 255, 255, 0.88);
  font: 400 0.98rem/1.3 Arial, sans-serif;
}
.paper-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(290px, 1fr));
  gap: 16px;
  margin-top: 24px;
}
.paper-card {
  border-radius: 22px;
  padding: 20px;
}
.paper-card h2 {
  margin: 14px 0 0;
  font-size: 1.36rem;
  line-height: 1.2;
}
.paper-card a {
  color: inherit;
  text-decoration: none;
}
.paper-card a:hover,
.back-link:hover {
  text-decoration: underline;
}
.paper-meta,
.detail-grid,
.link-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.pill {
  display: inline-flex;
  align-items: center;
  padding: 6px 10px;
  border-radius: 999px;
  background: var(--accent);
  color: white;
  font: 700 0.74rem/1 Arial, sans-serif;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
.pill.subtle {
  background: var(--accent-soft);
  color: #145046;
}
.at-a-glance,
.preview,
.detail-grid p,
.summary-article li {
  font: 400 0.98rem/1.6 Arial, sans-serif;
}
.preview {
  color: var(--muted);
}
.paper-shell .hero h1 {
  max-width: none;
}
.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
  gap: 14px;
  margin-top: 18px;
}
.link-row a,
.back-link {
  color: var(--accent);
  font: 700 0.92rem/1.3 Arial, sans-serif;
  text-decoration: none;
}
.summary-article {
  display: grid;
  gap: 16px;
  margin-top: 24px;
}
.summary-article section {
  border-radius: 22px;
  padding: 20px;
}
.summary-article h2 {
  margin-top: 0;
}
@media (max-width: 760px) {
  .toolbar {
    grid-template-columns: 1fr;
  }
}
"""
