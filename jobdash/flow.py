"""Build the application-flow (Sankey) diagram from each application's status path."""

from __future__ import annotations

from collections import Counter

import pandas as pd
import plotly.graph_objects as go

# Stages in pipeline order, then end states. "waiting" = applied, no reply yet.
STAGES = ["applied", "screen", "assessment", "interview", "offer"]
NODE_LABEL = {
    "applied": "Applications",
    "screen": "Recruiter screen",
    "assessment": "Assessment",
    "interview": "Interview",
    "offer": "Offer",
    "rejected": "Rejected",
    "withdrawn": "Withdrew",
    "ghosted": "Ghosted",
    "waiting": "No reply yet",
}
NODE_COLOR = {
    "applied": "#1c5cab",
    "screen": "#2a78d6",
    "assessment": "#5598e7",
    "interview": "#1baf7a",
    "offer": "#0ca30c",
    "rejected": "#d03b3b",
    "withdrawn": "#eda100",
    "ghosted": "#8a8984",
    "waiting": "#c3c2b7",
}
ORDER = STAGES + ["rejected", "withdrawn", "ghosted", "waiting"]


def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def flow_edges(paths: pd.DataFrame) -> Counter:
    """Count transitions between nodes across all applications."""
    edges: Counter = Counter()
    for _, row in paths.iterrows():
        path = [s for s in (row["path"] or []) if s in ORDER]
        # Every application starts at "applied", and repeated statuses collapse.
        steps: list[str] = ["applied"]
        for s in path:
            if s != steps[-1] and s != "applied":
                steps.append(s)
        current = row["status"]
        if current != steps[-1] and current in ORDER and current != "applied":
            steps.append(current)
        if steps == ["applied"]:
            steps.append("waiting")
        for a, b in zip(steps, steps[1:]):
            edges[(a, b)] += 1
    return edges


def sankey_figure(paths: pd.DataFrame) -> go.Figure | None:
    edges = flow_edges(paths)
    if not edges:
        return None
    used = sorted({n for e in edges for n in e}, key=ORDER.index)
    index = {n: i for i, n in enumerate(used)}
    inflow = Counter()
    outflow = Counter()
    for (a, b), n in edges.items():
        outflow[a] += n
        inflow[b] += n
    totals = {n: max(inflow[n], outflow[n]) for n in used}

    fig = go.Figure(
        go.Sankey(
            arrangement="snap",
            node=dict(
                label=[f"{NODE_LABEL[n]}  {totals[n]}" for n in used],
                color=[NODE_COLOR[n] for n in used],
                pad=22,
                thickness=14,
                line=dict(width=0),
                hovertemplate="%{label}<extra></extra>",
            ),
            link=dict(
                source=[index[a] for a, _ in edges],
                target=[index[b] for _, b in edges],
                value=list(edges.values()),
                color=[_hex_to_rgba(NODE_COLOR[b], 0.35) for _, b in edges],
                hovertemplate="%{source.label} → %{target.label}: %{value}<extra></extra>",
            ),
            textfont=dict(color="#0b0b0b", size=13),
        )
    )
    fig.update_layout(
        height=380,
        margin=dict(l=8, r=8, t=8, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig
