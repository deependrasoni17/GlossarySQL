"""GlossarySQL demo (Gradio).

    PYTHONPATH=src python app/app.py            # needs a running vLLM / OpenAI-compatible endpoint
    GLOSSARYSQL_LLM_BASE_URL=http://host:8000/v1 GLOSSARYSQL_LLM_MODEL=Qwen/Qwen2.5-Coder-7B-Instruct ...

Tabs: answer (summary, table, chart, confidence badge), SQL, retrieved context,
agent trace, evaluation results. When candidates disagree the graph pauses
(LangGraph interrupt) and the user picks one of the two most common answers.
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import gradio as gr  # noqa: E402
import pandas as pd  # noqa: E402
import plotly.express as px  # noqa: E402
from langgraph.checkpoint.memory import MemorySaver  # noqa: E402
from langgraph.types import Command  # noqa: E402

from glossarysql import paths  # noqa: E402
from glossarysql.agent.graph import GlossarySQLAgent  # noqa: E402
from glossarysql.data import load_minidev  # noqa: E402
from glossarysql.eval.run import load_config  # noqa: E402
from glossarysql.llm import LLM  # noqa: E402
from glossarysql.retrieval.knowledge_base import KnowledgeBase  # noqa: E402

MAX_QUESTIONS_PER_SESSION = int(os.environ.get("GLOSSARYSQL_MAX_Q", "30"))


def calibrated_threshold(default: float = 1.0) -> float:
    """Lowest vote-agreement threshold accepted by Learn-then-Test (alpha=0.3, delta=0.1) on E2_full."""
    f = paths.TABLES / "summary.json"
    try:
        t = json.loads(f.read_text())["calibration"]["demo_threshold_alpha0.3"]["threshold"]
        return float(t) if t is not None else 1.01
    except Exception:  # noqa: BLE001
        return default


CFG = load_config(str(paths.CONFIGS / "E2_full.yaml"))
CFG.update({"explain": True, "hitl": True, "threshold": calibrated_threshold()})
KB = KnowledgeBase()
AGENT = GlossarySQLAgent(KB, LLM(), CFG, checkpointer=MemorySaver())
EXAMPLES = load_minidev()
QID_BY_TEXT = {(e.db_id, e.question): e.question_id for e in EXAMPLES}
DBS = sorted({e.db_id for e in EXAMPLES})


def example_questions(db_id: str) -> list[str]:
    return [e.question for e in EXAMPLES if e.db_id == db_id and e.difficulty != "challenging"][:6]


def chart_figure(state: dict):
    chart = state.get("chart") or {}
    rows, cols = state.get("winner_rows") or [], state.get("winner_columns") or []
    if not rows or chart.get("type") in (None, "none", "table", "number"):
        return None
    df = pd.DataFrame(rows[:200], columns=cols)
    x, y = chart["x"], chart["y"]
    fn = px.line if chart["type"] == "line" else px.bar
    fig = fn(df, x=x, y=y, template="simple_white", color_discrete_sequence=["#2a78d6"])
    fig.update_layout(height=320, margin=dict(l=10, r=10, t=30, b=10))
    return fig


def badge(state: dict) -> str:
    conf = state.get("confidence", 0.0)
    n = len(state.get("candidates", [])) or 1
    agree = round(conf * n)
    decision = state.get("decision", "")
    label = {"answer": "Answered", "answer (user-picked)": "Answered with your pick"}.get(decision, "Abstained")
    return (f"**{label}** · {agree} of {n} candidate queries agree (confidence {conf:.0%}; "
            f"calibrated threshold {CFG['threshold']:.0%})")


def render(state: dict, pending: dict | None):
    rows, cols = state.get("winner_rows") or [], state.get("winner_columns") or []
    table = pd.DataFrame(rows[:500], columns=cols) if cols else pd.DataFrame()
    if pending:
        opts = pending["options"]
        lines = ["**Low agreement - the agent will not guess.** Pick the answer that fits:\n"]
        for i, o in enumerate(opts):
            lines.append(f"**Option {i + 1}** ({o['size']} of {len(state['candidates'])} candidates, "
                         f"{o['n_rows']} rows)\n```sql\n{o['sql']}\n```")
        answer_md = "\n".join(lines)
        choice_update = gr.update(choices=[f"Option {i + 1}" for i in range(len(opts))], value=None,
                                  visible=True)
    else:
        number = ""
        if (state.get("chart") or {}).get("type") == "number" and rows:
            number = f"\n\n# {rows[0][0]}"
        answer_md = f"{state.get('summary', '')}{number}\n\n{badge(state)}"
        choice_update = gr.update(visible=False, choices=[], value=None)
    sql_md = f"```sql\n{state.get('winner_sql', '')}\n```"
    ctx = state.get("context", {})
    ctx_md = ["### Glossary definitions"] + [f"- {g['text']}  _(sim {g['score']})_" for g in ctx.get("glossary", [])]
    ctx_md += ["### Matched values"] + [f"- `{v}`" for v in ctx.get("values", [])]
    ctx_md += ["### Solved examples"] + [f"- {e['question']}\n  `{e['sql']}`" for e in ctx.get("examples", [])]
    ctx_md += ["### Columns shown to the model", ", ".join(f"`{c}`" for c in ctx.get("columns", []))]
    groups = state.get("vote_groups", [])
    trace_md = [f"**Path:** {' → '.join(state.get('trace', []))}",
                f"**Repair rounds:** {state.get('attempts', 0)}",
                "### Candidates"]
    for i, c in enumerate(state.get("candidates", [])):
        r = (state.get("results") or [{}] * 5)[i] if i < len(state.get("results", [])) else {}
        status = "ok" if r.get("ok") else f"error: {r.get('error')}"
        trace_md.append(f"{i + 1}. _{c.get('origin')}_ · {status}\n```sql\n{c['sql']}\n```")
    trace_md.append("### Vote groups (identical result tables)")
    trace_md += [f"- {g['size']} vote(s): candidates {[m + 1 for m in g['members']]}, {g['n_rows']} rows"
                 for g in groups]
    usage = state.get("usage", [])
    toks = sum(u.get("prompt_tokens", 0) + u.get("completion_tokens", 0) for u in usage)
    trace_md.append(f"\n**LLM calls:** {sum(u.get('calls', 0) for u in usage)} · **tokens:** {toks}")
    return (answer_md, table, chart_figure(state), sql_md, "\n".join(ctx_md), "\n\n".join(trace_md),
            choice_update)


def ask(question: str, db_id: str, session: dict):
    session = dict(session or {})
    if not question.strip():
        raise gr.Error("Type a question first.")
    if session.get("count", 0) >= MAX_QUESTIONS_PER_SESSION:
        raise gr.Error("Question limit for this session reached.")
    session["count"] = session.get("count", 0) + 1
    thread = str(uuid.uuid4())
    session["thread"] = thread
    config = {"configurable": {"thread_id": thread}, "recursion_limit": 50}
    qid = QID_BY_TEXT.get((db_id, question.strip()))
    AGENT.graph.invoke({"question": question.strip(), "db_id": db_id, "fold": None, "evidence": "",
                        "exclude_qid": qid, "usage": [], "trace": []}, config=config)
    snap = AGENT.graph.get_state(config)
    pending = snap.tasks[0].interrupts[0].value if snap.tasks and snap.tasks[0].interrupts else None
    return (*render(snap.values, pending), session)


def pick(choice: str, session: dict):
    if not choice or not session.get("thread"):
        raise gr.Error("Pick an option first.")
    config = {"configurable": {"thread_id": session["thread"]}, "recursion_limit": 50}
    AGENT.graph.invoke(Command(resume=int(choice.split()[-1]) - 1), config=config)
    snap = AGENT.graph.get_state(config)
    return (*render(snap.values, None), session)


def evaluation_md() -> str:
    parts = ["## Evaluation on BIRD Mini-Dev (500 questions, two-fold knowledge/evaluation split)"]
    for name in ("main_results.md", "significance.md"):
        f = paths.TABLES / name
        if f.exists():
            parts.append(f.read_text())
    return "\n\n".join(parts)


with gr.Blocks(title="GlossarySQL") as demo:
    gr.Markdown("# GlossarySQL\nAsk a business question in plain English. The agent retrieves schema, values, "
                "**business definitions** and solved examples, writes 5 SQL candidates, repairs failures, "
                "votes on result tables, and abstains when the candidates disagree.")
    session = gr.State({})
    with gr.Row():
        db = gr.Dropdown(DBS, value="california_schools", label="Database", scale=1)
        q = gr.Textbox(label="Question", scale=4,
                       placeholder="Which schools in Alameda have the highest eligible free-meal rate?")
    ex_box = gr.Dropdown(example_questions("california_schools"), label="Example questions")
    btn = gr.Button("Ask", variant="primary")
    with gr.Tabs():
        with gr.Tab("Answer"):
            answer = gr.Markdown()
            choice = gr.Radio(label="Your pick", visible=False)
            pick_btn = gr.Button("Use this answer")
            chart = gr.Plot()
            table = gr.Dataframe(wrap=True)
        with gr.Tab("SQL"):
            sql = gr.Markdown()
        with gr.Tab("Retrieved context"):
            ctx = gr.Markdown()
        with gr.Tab("Agent trace"):
            trace = gr.Markdown()
        with gr.Tab("Evaluation"):
            gr.Markdown(evaluation_md())
            for fig in ("ex_by_config.png", "risk_coverage.png", "error_analysis.png"):
                if (paths.FIGURES / fig).exists():
                    gr.Image(str(paths.FIGURES / fig), show_label=False)
    outputs = [answer, table, chart, sql, ctx, trace, choice, session]
    db.change(lambda d: gr.update(choices=example_questions(d), value=None), db, ex_box)
    ex_box.change(lambda x: x or gr.update(), ex_box, q)
    btn.click(ask, [q, db, session], outputs)
    q.submit(ask, [q, db, session], outputs)
    pick_btn.click(pick, [choice, session], outputs)

if __name__ == "__main__":
    demo.queue(default_concurrency_limit=4).launch(
        server_name=os.environ.get("GRADIO_SERVER_NAME", "0.0.0.0"),
        server_port=int(os.environ.get("GRADIO_SERVER_PORT", "7860")))
