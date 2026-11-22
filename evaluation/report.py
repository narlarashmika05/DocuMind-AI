"""Markdown tables and PNG charts for evaluation results.

Chart rules (see docs): one axis, at most three series per chart using the first three
validated categorical colours, thin bars with rounded tops, recessive grid, legend for
2+ series, values in text colour.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # render to files, no window
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]  # categorical slots 1-3 (validated all-pairs, light mode)
SURFACE, TEXT_PRIMARY, TEXT_SECONDARY, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"

LANGUAGE_LABELS = {"en": "English questions", "te": "Telugu questions", "te_raw": "Telugu, no translation"}


def _style(ax, title: str, ylabel: str) -> None:
    ax.set_facecolor(SURFACE)
    ax.set_title(title, loc="left", fontsize=12, color=TEXT_PRIMARY, pad=12)
    ax.set_ylabel(ylabel, color=TEXT_SECONDARY, fontsize=9)
    ax.tick_params(colors=TEXT_SECONDARY, labelsize=9, length=0)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)


def grouped_bars(path: Path, title: str, groups: list[str], series: dict[str, list[float]], ylabel: str) -> None:
    fig, ax = plt.subplots(figsize=(7.5, 3.8), facecolor=SURFACE)
    n = len(series)
    width = 0.8 / n
    gap = 0.02  # thin surface gap between neighbouring bars
    for i, (label, values) in enumerate(series.items()):
        for j, value in enumerate(values):
            x = j - 0.4 + i * width + gap / 2
            ax.add_patch(FancyBboxPatch((x, 0), width - gap, value, boxstyle="round,pad=0,rounding_size=0.02",
                                        mutation_aspect=0.05, linewidth=0, facecolor=SERIES[i], label=label if j == 0 else None))
            ax.text(x + (width - gap) / 2, value + 0.015, f"{value:.2f}", ha="center", va="bottom", fontsize=7.5, color=TEXT_SECONDARY)
    ax.set_xlim(-0.6, len(groups) - 0.4)
    ax.set_ylim(0, 1.08)
    ax.set_xticks(range(len(groups)), groups)
    _style(ax, title, ylabel)
    if n > 1:
        ax.legend(frameon=False, fontsize=8.5, labelcolor=TEXT_SECONDARY, loc="upper left", bbox_to_anchor=(0, -0.12), ncol=n)
    fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor=SURFACE)
    plt.close(fig)


def lines(path: Path, title: str, x: list[float], series: dict[str, list[float]], xlabel: str, ylabel: str) -> None:
    fig, ax = plt.subplots(figsize=(7.5, 3.8), facecolor=SURFACE)
    for i, (label, values) in enumerate(series.items()):
        ax.plot(x, values, color=SERIES[i], linewidth=2, marker="o", markersize=5, label=label)
        ax.annotate(label, (x[-1], values[-1]), xytext=(6, 0), textcoords="offset points", fontsize=8,
                    color=TEXT_SECONDARY, va="center")  # direct label at the line end
    ax.set_ylim(0, 1.05)
    ax.set_xlabel(xlabel, color=TEXT_SECONDARY, fontsize=9)
    _style(ax, title, ylabel)
    ax.legend(frameon=False, fontsize=8.5, labelcolor=TEXT_SECONDARY, loc="upper left", bbox_to_anchor=(0, -0.18), ncol=len(series))
    fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor=SURFACE)
    plt.close(fig)


def _table(rows: list[dict], columns: list[str]) -> str:
    header = "| " + " | ".join(columns) + " |\n|" + "---|" * len(columns)
    body = ["| " + " | ".join(_fmt(row.get(c)) for c in columns) + " |" for row in rows]
    return "\n".join([header, *body])


def _fmt(value) -> str:
    return f"{value:.3f}" if isinstance(value, float) else str(value)


def write_retrieval_report(results: dict, out_dir: Path) -> None:
    charts = out_dir / "charts"
    charts.mkdir(parents=True, exist_ok=True)
    experiments = results["experiments"]
    metric_cols = ["mrr", "precision@1", "precision@3", "recall@3", "recall@5", "hit@5", "latency_ms_mean"]
    lines_md = [f"# Retrieval evaluation – {results['name']}", "",
                f"Dataset: {results['dataset']['answerable']} answerable questions over {results['dataset']['documents']} "
                f"documents ({results['dataset']['pages']} pages). Relevance is judged by gold page.", ""]

    if "embedding_models" in experiments:
        rows = experiments["embedding_models"]["rows"]
        lines_md += ["## Embedding models (dense retrieval)", "", _table(rows, ["model", "language", *metric_cols]), ""]
        models = list(dict.fromkeys(r["model"] for r in rows))
        series = {LANGUAGE_LABELS[lang]: [next(r["mrr"] for r in rows if r["model"] == m and r["language"] == lang) for m in models]
                  for lang in dict.fromkeys(r["language"] for r in rows)}
        grouped_bars(charts / "embedding_models_mrr.png", "Embedding models: MRR by question language", models, series, "MRR")

    if "chunking" in experiments:
        rows = experiments["chunking"]["rows"]
        lines_md += ["## Chunking strategies and sizes (hybrid, English)", "",
                     _table(rows, ["strategy", "chunk_size", "chunks", *metric_cols]), ""]
        sizes = list(dict.fromkeys(r["chunk_size"] for r in rows))
        strategies = list(dict.fromkeys(r["strategy"] for r in rows))
        series = {s: [next(r["mrr"] for r in rows if r["strategy"] == s and r["chunk_size"] == size) for size in sizes]
                  for s in strategies}
        grouped_bars(charts / "chunking.png", "Chunking: MRR by chunk size (tokens)", [f"{s} tokens" for s in sizes], series, "MRR")

    if "retrieval_modes" in experiments:
        rows = experiments["retrieval_modes"]["rows"]
        lines_md += ["## Retrieval modes and reranking", "", _table(rows, ["mode", "rerank", "language", *metric_cols]), ""]
        configs = list(dict.fromkeys((r["mode"], r["rerank"]) for r in rows))
        labels = [f"{mode}{' + rerank' if rerank else ''}" for mode, rerank in configs]
        series = {LANGUAGE_LABELS[lang]: [next(r["mrr"] for r in rows if (r["mode"], r["rerank"]) == c and r["language"] == lang) for c in configs]
                  for lang in dict.fromkeys(r["language"] for r in rows)}
        grouped_bars(charts / "retrieval_modes_mrr.png", "Retrieval configuration: MRR", labels, series, "MRR")

    if "gate" in results:
        gate = results["gate"]
        lines_md += ["## Relevance gate (refuse when best reranker score < threshold)", "",
                     _table(gate, ["threshold", "answerable_answered", "unanswerable_refused"]), ""]
        lines(charts / "relevance_gate.png", "Relevance gate trade-off", [r["threshold"] for r in gate],
              {"Answerable questions answered": [r["answerable_answered"] for r in gate],
               "Unanswerable questions refused": [r["unanswerable_refused"] for r in gate]},
              "Threshold on best reranker probability", "Share of questions")

    lines_md += ["## Charts", ""] + [f"![{p.stem}](charts/{p.name})" for p in sorted(charts.glob("*.png"))]
    (out_dir / "summary.md").write_text("\n".join(lines_md) + "\n", encoding="utf-8")


def write_verifier_report(results: dict, out_dir: Path) -> None:
    m = results["binary"]
    lines_md = [
        f"# Hallucination detector evaluation – {results['name']}", "",
        f"{results['total']} labelled claims ({results['label_counts']}). Positive class = hallucination "
        "(gold label unsupported or contradicted).", "",
        f"- Precision: **{m['precision']:.3f}**  (flagged claims that really were hallucinations)",
        f"- Recall: **{m['recall']:.3f}**  (hallucinations that were caught)",
        f"- F1: **{m['f1']:.3f}**, accuracy {m['accuracy']:.3f}",
        f"- Exact 3-class verdict accuracy: **{results['three_class_accuracy']:.3f}**", "",
        "## Confusion matrix (rows = gold, columns = predicted)", "",
        _table([{"gold": g, **counts} for g, counts in results["confusion"].items()],
               ["gold", "supported", "partially_supported", "unsupported", "contradicted", "not_checked"]), "",
        "## Errors", "",
        _table(results["errors"], ["id", "gold", "predicted", "confidence", "claim"]) if results["errors"] else "None.", "",
    ]
    (out_dir / "summary.md").write_text("\n".join(lines_md) + "\n", encoding="utf-8")
