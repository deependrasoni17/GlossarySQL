"""The GlossarySQL agent as a LangGraph StateGraph.

    retrieve -> generate -> guard -> execute --(failures & attempts < max)--> repair -> guard
                                         \\--> vote --(confidence >= threshold)--> explain -> END
                                                    \\--> abstain (optional human pick) -> END

Every experiment configuration (A-F) is this same graph; the YAML config only
switches parts on or off (number of candidates, repair budget, which indexes).
"""

from __future__ import annotations

import operator
import time
from collections import Counter
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from glossarysql import paths
from glossarysql.agent import prompts
from glossarysql.llm import LLM
from glossarysql.retrieval.knowledge_base import Context, KnowledgeBase
from glossarysql.sql.executor import execute_sql
from glossarysql.sql.guard import check_sql
from glossarysql.sql.normalize import result_key


class AgentState(TypedDict, total=False):
    question: str
    db_id: str
    fold: int | None
    evidence: str
    exclude_qid: int | None
    context: dict
    candidates: list[dict]  # {"reasoning", "sql", "origin"}
    results: list[dict]  # per candidate: {"ok", "rows", "columns", "error", "guard"}
    attempts: int
    winner_idx: int
    winner_sql: str
    winner_rows: list
    winner_columns: list[str]
    confidence: float
    vote_groups: list[dict]
    decision: str
    summary: str
    chart: dict
    usage: Annotated[list[dict], operator.add]
    trace: Annotated[list[str], operator.add]


def choose_chart(columns: list[str], rows: list[tuple]) -> dict:
    """Simple rules: one value -> big number; date + number -> line; category + number -> bar."""
    if not rows or not columns:
        return {"type": "none"}
    if len(rows) == 1 and len(columns) == 1:
        return {"type": "number"}
    if len(columns) >= 2 and len(rows) > 1:
        first = [r[0] for r in rows[:50]]
        second_numeric = all(isinstance(r[1], (int, float)) or r[1] is None for r in rows[:50])
        if second_numeric:
            name = columns[0].lower()
            datey = any(k in name for k in ("date", "year", "month", "time", "day", "season"))
            if datey or all(isinstance(v, str) and v[:4].isdigit() and "-" in v for v in first if v):
                return {"type": "line", "x": columns[0], "y": columns[1]}
            return {"type": "bar", "x": columns[0], "y": columns[1]}
    return {"type": "table"}


class GlossarySQLAgent:
    def __init__(self, kb: KnowledgeBase, llm: LLM | None, cfg: dict, checkpointer=None):
        self.kb, self.llm, self.cfg = kb, llm, cfg
        self.graph = self._build().compile(checkpointer=checkpointer)

    # ---------------- helpers ----------------
    def _rebuild(self, state: AgentState) -> Context:
        # The state keeps a JSON-friendly copy of the context; the full objects are
        # rebuilt from the KB's caches (cheap) so the state stays serialisable.
        return self.kb.build_context(state["question"], state["db_id"], self.cfg, state.get("fold"),
                                     evidence=state.get("evidence", ""),
                                     exclude_qid=state.get("exclude_qid"))

    def _usage(self, node: str, resp, t0: float) -> dict:
        return {"node": node, "calls": 1, "prompt_tokens": resp.prompt_tokens,
                "completion_tokens": resp.completion_tokens, "llm_seconds": resp.seconds,
                "cached": resp.cached, "wall": time.perf_counter() - t0}

    # ---------------- nodes ----------------
    def retrieve(self, state: AgentState) -> dict:
        t0 = time.perf_counter()
        ctx = self._rebuild(state)
        return {"context": ctx.to_dict(), "attempts": 0, "trace": ["retrieve"],
                "usage": [{"node": "retrieve", "calls": 0, "wall": time.perf_counter() - t0}]}

    def generate(self, state: AgentState) -> dict:
        t0 = time.perf_counter()
        ctx = self._rebuild(state)
        n = self.cfg.get("n_candidates", 1)
        temp = self.cfg.get("temperature", 0.0) if n > 1 else 0.0
        resp = self.llm.chat(prompts.SYSTEM, prompts.generation_prompt(state["question"], ctx),
                             temperature=temp, n=n, max_tokens=self.cfg.get("max_tokens", 768),
                             seed=self.cfg.get("seed", 0))
        cands = [dict(prompts.parse_candidate(t).model_dump(), origin="generate") for t in resp.texts]
        return {"candidates": cands, "results": [{} for _ in cands], "trace": ["generate"],
                "usage": [self._usage("generate", resp, t0)]}

    def guard(self, state: AgentState) -> dict:
        results = [dict(r) for r in state["results"]]
        for i, c in enumerate(state["candidates"]):
            if results[i]:  # already executed in an earlier round
                continue
            g = check_sql(c["sql"])
            results[i] = {"guard": g.reason} if g.ok else {"ok": False, "error": f"rejected by guard: {g.reason}",
                                                          "guard": g.reason}
            c["sql"] = g.sql
        return {"results": results, "candidates": state["candidates"], "trace": ["guard"]}

    def execute(self, state: AgentState) -> dict:
        t0 = time.perf_counter()
        results = [dict(r) for r in state["results"]]
        db = paths.db_path(state["db_id"])
        done: dict[str, dict] = {}
        for i, c in enumerate(state["candidates"]):
            if "ok" in results[i]:
                continue
            if c["sql"] in done:  # identical SQL: execute once
                results[i] = {**done[c["sql"]], "guard": results[i].get("guard", "")}
                continue
            r = execute_sql(db, c["sql"], timeout_s=self.cfg.get("sql_timeout", 30),
                            max_rows=self.cfg.get("max_rows", 100_000))
            results[i] = {"ok": r.ok, "rows": r.rows, "columns": r.columns, "error": r.error,
                          "elapsed": r.elapsed, "guard": results[i].get("guard", "")}
            done[c["sql"]] = results[i]
        return {"results": results, "trace": ["execute"],
                "usage": [{"node": "execute", "calls": 0, "wall": time.perf_counter() - t0}]}

    def route_after_execute(self, state: AgentState) -> str:
        failed = any(not r.get("ok") for r in state["results"])
        if failed and state.get("attempts", 0) < self.cfg.get("max_repairs", 0):
            return "repair"
        return "vote"

    def repair(self, state: AgentState) -> dict:
        t0 = time.perf_counter()
        ctx = self._rebuild(state)
        cands = [dict(c) for c in state["candidates"]]
        results = [dict(r) for r in state["results"]]
        usage, fixed = [], {}
        for i, (c, r) in enumerate(zip(cands, results)):
            if r.get("ok"):
                continue
            key = (c["sql"], r.get("error"))
            if key not in fixed:
                resp = self.llm.chat(prompts.SYSTEM, prompts.repair_prompt(
                    state["question"], ctx, c["sql"], r.get("error") or "unknown error"),
                    temperature=0.0, n=1, max_tokens=self.cfg.get("max_tokens", 768), seed=0)
                fixed[key] = prompts.parse_candidate(resp.texts[0])
                usage.append(self._usage("repair", resp, t0))
            cands[i] = dict(fixed[key].model_dump(), origin=f"repair{state.get('attempts', 0) + 1}")
            results[i] = {}
        return {"candidates": cands, "results": results, "attempts": state.get("attempts", 0) + 1,
                "trace": ["repair"], "usage": usage}

    def vote(self, state: AgentState) -> dict:
        n = len(state["candidates"])
        groups: dict[frozenset, list[int]] = {}
        for i, r in enumerate(state["results"]):
            if r.get("ok"):
                groups.setdefault(result_key(r["rows"]), []).append(i)
        if not groups:
            return {"winner_idx": 0, "winner_sql": state["candidates"][0]["sql"] if n else "",
                    "winner_rows": [], "winner_columns": [], "confidence": 0.0, "vote_groups": [],
                    "trace": ["vote"]}
        # Largest group wins; ties prefer a non-empty result, then the earliest candidate.
        ordered = sorted(groups.items(), key=lambda kv: (-len(kv[1]), len(kv[0]) == 0, kv[1][0]))
        best = ordered[0][1]
        w = best[0]
        res = state["results"][w]
        vote_groups = [{"size": len(ix), "members": ix, "sql": state["candidates"][ix[0]]["sql"],
                        "n_rows": len(state["results"][ix[0]]["rows"])} for _, ix in ordered]
        return {"winner_idx": w, "winner_sql": state["candidates"][w]["sql"],
                "winner_rows": res["rows"], "winner_columns": res["columns"],
                "confidence": len(best) / n, "vote_groups": vote_groups, "trace": ["vote"]}

    def route_decide(self, state: AgentState) -> str:
        return "explain" if state["confidence"] >= self.cfg.get("threshold", 0.0) else "abstain"

    def abstain(self, state: AgentState) -> dict:
        update: dict[str, Any] = {"decision": "abstain", "trace": ["abstain"]}
        if self.cfg.get("hitl", False) and len(state.get("vote_groups", [])) >= 1:
            options = state["vote_groups"][:2]
            # Pauses the graph; the demo resumes it with Command(resume=<group index>).
            choice = interrupt({"message": "Low agreement between candidates. Pick an answer.",
                                "options": options})
            if choice is not None and 0 <= int(choice) < len(options):
                idx = options[int(choice)]["members"][0]
                r = state["results"][idx]
                update.update({"decision": "answer (user-picked)", "winner_idx": idx,
                               "winner_sql": state["candidates"][idx]["sql"],
                               "winner_rows": r["rows"], "winner_columns": r["columns"]})
                update.update(self._explain_fields({**state, **update}))
        return update

    def _explain_fields(self, state: AgentState) -> dict:
        rows, cols = state.get("winner_rows", []), state.get("winner_columns", [])
        out: dict[str, Any] = {"chart": choose_chart(cols, rows)}
        if self.cfg.get("explain", False) and self.llm is not None:
            preview = "\n".join(str(r) for r in rows[:10])
            resp = self.llm.chat(
                "You summarise query results for business users in one plain sentence.",
                f"Question: {state['question']}\nSQL: {state.get('winner_sql')}\nColumns: {cols}\n"
                f"First rows:\n{preview}\nTotal rows: {len(rows)}\n\nAnswer the question in one sentence.",
                temperature=0.0, n=1, max_tokens=120, seed=0)
            out["summary"] = resp.texts[0].strip()
            out["usage"] = [self._usage("explain", resp, time.perf_counter())]
        return out

    def explain(self, state: AgentState) -> dict:
        return {"decision": "answer", "trace": ["explain"], **self._explain_fields(state)}

    # ---------------- graph ----------------
    def _build(self) -> StateGraph:
        g = StateGraph(AgentState)
        for name in ("retrieve", "generate", "guard", "execute", "repair", "vote", "explain", "abstain"):
            g.add_node(name, getattr(self, name))
        g.add_edge(START, "retrieve")
        g.add_edge("retrieve", "generate")
        g.add_edge("generate", "guard")
        g.add_edge("guard", "execute")
        g.add_conditional_edges("execute", self.route_after_execute, {"repair": "repair", "vote": "vote"})
        g.add_edge("repair", "guard")
        g.add_conditional_edges("vote", self.route_decide, {"explain": "explain", "abstain": "abstain"})
        g.add_edge("explain", END)
        g.add_edge("abstain", END)
        return g

    def run(self, question: str, db_id: str, fold: int | None = None, evidence: str = "",
            exclude_qid: int | None = None, config: dict | None = None) -> AgentState:
        init: AgentState = {"question": question, "db_id": db_id, "fold": fold, "evidence": evidence,
                            "exclude_qid": exclude_qid, "usage": [], "trace": []}
        return self.graph.invoke(init, config=config or {"recursion_limit": 50})


def summarize_usage(usage: list[dict]) -> dict:
    c = Counter()
    for u in usage:
        for k in ("calls", "prompt_tokens", "completion_tokens", "llm_seconds", "wall"):
            c[k] += u.get(k, 0) or 0
    return dict(c)
