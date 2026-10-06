import arxiv

import evidence_db as db


def search_arxiv(query: str, max_results: int = 5, db_path=db.DB_PATH) -> list[dict]:
    """Search arXiv, save every paper found into the evidence store,
    and return a short summary list that includes each paper's source_id."""
    client = arxiv.Client(page_size=max_results, delay_seconds=3, num_retries=2)
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance,
    )

    results = []
    for paper in client.results(search):
        authors = ", ".join(a.name for a in paper.authors)
        text = (
            f"{paper.title}\n\n"
            f"Authors: {authors}\n"
            f"Published: {paper.published.date()}\n\n"
            f"{paper.summary}"
        )
        source_id = db.add_source(paper.entry_id, paper.title, text, "arxiv", db_path)
        results.append({
            "source_id": source_id,
            "title": paper.title,
            "url": paper.entry_id,
            "published": str(paper.published.date()),
        })
    return results