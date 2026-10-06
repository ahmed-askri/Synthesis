# Synthesis
[![CI](https://github.com/ahmed-askri/Synthesis/actions/workflows/ci.yml/badge.svg)](https://github.com/ahmed-askri/Synthesis/actions)
A research assistant for AI agent engineering. Ask a question, and Synthesis finds relevant arXiv papers, extracts claims, checks each claim against its source, and writes a short report where every sentence cites a real paper.

> Work in progress. The core pipeline and web interface work. Guardrails, the multi-agent rebuild and the evaluation suite are next.

## How it works

1. **Plan the search.** The question becomes an arXiv query (concept groups, restricted to AI categories).
2. **Extract claims.** The model reads the papers and proposes single-fact claims, each tied to real source IDs.
3. **Check every claim.** A fact-checker must return a verbatim quote from the source. The code verifies the quote exists. Anything it cannot verify is rejected, and garbled answers fail closed.
4. **Write the report.** The writer only sees verified claims. Every sentence needs a citation, citations must point to real sources, and a report that fails these checks is not shown.

All state lives in a SQLite evidence store, so the writer cannot cite a source that was never retrieved.

## Run it

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env      # then add your GROQ_API_KEY
python server.py            # web interface at http://localhost:8000
```

Or from the terminal: `python pipeline.py "How do multi-agent LLM systems fail?"`

Run the tests (offline, no API keys needed): `python -m pytest -q`

## Limitations

- Claims are checked against paper abstracts, not full texts.
- The fact-checker is an LLM. Quote verification proves a quote exists, not that it covers every part of the claim.
- Search is keyword-based, so coverage depends on how arXiv indexes a topic.

## Roadmap

- Injection scanner and quarantine for untrusted sources, human approval before saving
- Multi-agent versions in CrewAI and LangGraph, with per-role tool permissions
- Search tools exposed as an MCP server
- Evaluation scenarios run through [AgentLens](https://github.com/ahmed-askri/AgentLens)

Built by Ahmed Askri, Computer Science Engineering student, ENSI Tunisia.
