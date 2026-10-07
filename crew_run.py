import os
import sys
from pathlib import Path

os.environ.setdefault("OTEL_SDK_DISABLED", "true")
os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")

from dotenv import load_dotenv

load_dotenv()

from crewai import Agent, Crew, LLM, Process, Task
from crewai.tools import tool

import evidence_db as db
import fact_checker
import researcher
import writer
from guardrails.approval import cli_approve, save_with_approval
from guardrails.sanitize import scan_sources
from pipeline import make_registry
from query_planner import plan_groups, search_with_relaxation
from tools.web_search import TRUSTED_DOMAINS

DB = "crew.db"
REG = make_registry(DB)
STATE = {"question": "", "sources": [], "done": set(), "out": None}


# ---- Tools: the guardrails live INSIDE them, the agent cannot skip them ----

@tool("search_sources")
def search_sources(query: str) -> str:
    """Search arXiv and trusted web sources for the research question,
    then scan them for prompt injection. Input: the research question."""
    q = STATE["question"]
    found, _ = search_with_relaxation(
        plan_groups(q),
        lambda x: REG.call("researcher", "search_arxiv", query=x, max_results=5))
    if not found:
        found = REG.call("researcher", "search_arxiv", query=q, max_results=5)
    try:
        found += REG.call("researcher", "search_web", query=q, max_results=3,
                          include_domains=TRUSTED_DOMAINS)
    except Exception:
        pass
    ids = [p["source_id"] for p in found]
    flagged = scan_sources(ids, DB)
    STATE["sources"] = ids
    STATE["done"].add("search")
    return f"Found {len(ids)} sources, {len(flagged)} excluded as suspicious."


@tool("extract_claims")
def extract_claims(note: str) -> str:
    """Extract claims from the sources that were found. Input: any short note."""
    if "search" not in STATE["done"]:
        return "Run search_sources first."
    researcher.extract_claims(STATE["question"], STATE["sources"], DB)
    n = len(db.get_claims("unchecked", DB))
    STATE["done"].add("extract")
    return f"Extracted {n} claims."


@tool("check_claims")
def check_claims(note: str) -> str:
    """Fact-check all extracted claims against their sources. Input: any short note."""
    if "extract" not in STATE["done"]:
        return "Run extract_claims first."
    results = fact_checker.check_all(DB)
    STATE["done"].add("check")
    return f"Checked {len(results)} claims."


@tool("write_report")
def write_report(note: str) -> str:
    """Write the cited report from the verified claims. Input: any short note."""
    if "check" not in STATE["done"]:
        return "Run check_claims first."
    STATE["out"] = writer.write_report(STATE["question"], DB)
    STATE["done"].add("write")
    return f"Report written. citation check passed: {STATE['out']['ok']}"


def main():
    question = " ".join(sys.argv[1:]) or "How should LLM agents be evaluated?"
    Path(DB).unlink(missing_ok=True)
    db.init_db(DB)
    STATE.update(question=question, sources=[], done=set(), out=None)

    llm = LLM(
        model="openai/openai/gpt-oss-20b",
        base_url="https://api.groq.com/openai/v1",
        api_key=os.environ["GROQ_API_KEY"],
        temperature=0,
    )
    r = Agent(role="Researcher", goal="Find sources and extract claims",
              backstory="You collect evidence. You never invent facts.",
              tools=[search_sources, extract_claims], llm=llm,
              allow_delegation=False, verbose=True)
    f = Agent(role="Fact-checker", goal="Verify every claim against its source",
              backstory="You are strict and only trust the sources.",
              tools=[check_claims], llm=llm, allow_delegation=False, verbose=True)
    w = Agent(role="Writer", goal="Produce the cited report",
              backstory="You only write what was verified.",
              tools=[write_report], llm=llm, allow_delegation=False, verbose=True)

    tasks = [
        Task(description=f"Question: {question}\nCall search_sources, then extract_claims.",
             expected_output="Number of sources and claims.", agent=r),
        Task(description="Call check_claims.",
             expected_output="Number of claims checked.", agent=f),
        Task(description="Call write_report.",
             expected_output="Confirmation that the report was written.", agent=w),
    ]
    Crew(agents=[r, f, w], tasks=tasks, process=Process.sequential, verbose=True).kickoff()

    missing = [s for s in ("search", "extract", "check", "write") if s not in STATE["done"]]
    if missing:
        print(f"\nThe crew skipped these steps: {missing}")
        return
    out = STATE["out"]
    print("\n" + (out["report"] if out["ok"] else out["note"] or "Report rejected."))
    if out["ok"]:
        saved = save_with_approval(out["report"], cli_approve)
        print(f"saved to {saved}" if saved else "not saved (no approval)")


if __name__ == "__main__":
    main()