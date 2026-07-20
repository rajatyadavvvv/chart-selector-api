"""Renders a chosen chart type into a PNG image, with a full explanation of
what's being shown, what each axis represents, and what any colors mean."""

import io
import logging
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.edgecolor": "#333333",
    "axes.grid": True,
    "grid.color": "#dddddd",
    "grid.linewidth": 0.6,
    "font.size": 10,
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "axes.labelsize": 10,
})

PRIMARY_COLOR = "#4C72B0"
PALETTE = ["#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B2", "#937860", "#DA8BC3", "#8C8C8C"]
BAR_TOP_N = 20


class ChartRenderError(Exception):
    """Raised when a chart cannot be rendered."""


def render_chart(df: pd.DataFrame, decision) -> io.BytesIO:
    renderer = _RENDERERS.get(decision.chart_type)
    if renderer is None:
        raise ChartRenderError(f"Unsupported chart_type: {decision.chart_type}")

    fig, ax = plt.subplots(figsize=(8, 6.2), dpi=110)
    try:
        final_fig = renderer(df, decision, ax, fig) or fig
        explanation = _EXPLANATIONS[decision.chart_type](decision)
        axis_note = _AXIS_COLOR_NOTES[decision.chart_type](decision)
        _add_caption(final_fig, explanation, axis_note)
        final_fig.tight_layout(rect=[0, 0.14, 1, 1])

        buf = io.BytesIO()
        final_fig.savefig(buf, format="png", bbox_inches="tight")
        buf.seek(0)
        return buf
    except ChartRenderError:
        raise
    except Exception as exc:
        logger.exception("Chart rendering failed for type '%s'", decision.chart_type)
        raise ChartRenderError(f"Failed to render '{decision.chart_type}' chart: {exc}") from exc
    finally:
        plt.close("all")


def _add_caption(fig, explanation: str, axis_note: str):
    wrapped_explanation = "\n".join(textwrap.wrap(explanation, width=95))
    wrapped_axis_note = "\n".join(textwrap.wrap(axis_note, width=100))

    fig.text(0.5, 0.075, wrapped_explanation, ha="center", va="bottom",
              fontsize=8.8, color="#333333", weight="bold")
    fig.text(0.5, 0.01, wrapped_axis_note, ha="center", va="bottom",
              fontsize=7.8, color="#666666", style="italic")


# --- Renderers ---------------------------------------------------------

def _render_line(df, d, ax, fig):
    clean = df[[d.x, d.y]].dropna().sort_values(by=d.x)
    ax.plot(pd.to_datetime(clean[d.x]), clean[d.y], color=PRIMARY_COLOR, linewidth=2,
            linestyle='-', marker='o', label=d.y)
    ax.set_xlabel(f"{d.x} (time)")
    ax.set_ylabel(d.y)
    ax.set_title(f"{d.y} over {d.x}")
    ax.legend(loc="best", frameon=False, fontsize=8)
    fig.autofmt_xdate()


def _render_scatter(df, d, ax, fig):
    clean = df[[d.x, d.y]].dropna()
    ax.scatter(clean[d.x], clean[d.y], alpha=0.65, color=PRIMARY_COLOR,
               edgecolors="white", linewidths=0.4, label=f"{d.x} vs {d.y}")
    ax.set_xlabel(d.x)
    ax.set_ylabel(d.y)
    ax.set_title(f"{d.y} vs {d.x}")
    ax.legend(loc="best", frameon=False, fontsize=8)


def _render_bar(df, d, ax, fig):
    clean = df[[d.x, d.y]].dropna()
    grouped = clean.groupby(d.x)[d.y].mean().sort_values(ascending=False).head(BAR_TOP_N)
    ax.bar(grouped.index.astype(str), grouped.values, color=PRIMARY_COLOR, label=f"Average {d.y}")
    ax.set_xlabel(d.x)
    ax.set_ylabel(f"Average {d.y}")
    ax.set_title(f"Average {d.y} by {d.x} (top {BAR_TOP_N})")
    ax.legend(loc="best", frameon=False, fontsize=8)
    _rotate_labels(ax)


def _render_bar_count(df, d, ax, fig):
    counts = df[d.x].dropna().value_counts().head(BAR_TOP_N)
    ax.bar(counts.index.astype(str), counts.values, color=PRIMARY_COLOR, label="Number of rows")
    ax.set_xlabel(d.x)
    ax.set_ylabel("Count")
    ax.set_title(f"Count of {d.x} (top {BAR_TOP_N})")
    ax.legend(loc="best", frameon=False, fontsize=8)
    _rotate_labels(ax)


def _render_histogram(df, d, ax, fig):
    data = df[d.x].dropna()
    ax.hist(data, bins=30, color=PRIMARY_COLOR, edgecolor="white", density=True,
            alpha=0.85, label=f"{d.x} distribution")
    try:
        from scipy.stats import gaussian_kde
        kde = gaussian_kde(data)
        xs = np.linspace(data.min(), data.max(), 200)
        ax.plot(xs, kde(xs), color="#C44E52", linewidth=2, label="Smoothed density curve")
    except Exception:
        pass
    ax.set_xlabel(d.x)
    ax.set_ylabel("Density")
    ax.set_title(f"Distribution of {d.x}")
    ax.legend(loc="best", frameon=False, fontsize=8)


def _render_pie(df, d, ax, fig):
    counts = df[d.x].dropna().value_counts()
    ax.pie(counts.values, labels=counts.index.astype(str), autopct="%1.1f%%",
           colors=PALETTE, wedgeprops={"edgecolor": "white", "linewidth": 1})
    ax.set_title(f"Proportion of {d.x}")
    ax.grid(False)
    ax.legend(counts.index.astype(str), loc="center left", bbox_to_anchor=(1.0, 0.5),
              frameon=False, fontsize=8, title=d.x)


def _render_box(df, d, ax, fig):
    clean = df[[d.x, d.y]].dropna()
    categories = clean[d.x].unique()
    data = [clean[clean[d.x] == c][d.y] for c in categories]
    bp = ax.boxplot(data, tick_labels=[str(c) for c in categories], patch_artist=True)
    for patch in bp["boxes"]:
        patch.set_facecolor(PRIMARY_COLOR)
        patch.set_alpha(0.6)
    ax.set_xlabel(d.x)
    ax.set_ylabel(d.y)
    ax.set_title(f"Distribution of {d.y} by {d.x}")
    _rotate_labels(ax)


def _render_violin(df, d, ax, fig):
    clean = df[[d.x, d.y]].dropna()
    categories = clean[d.x].unique()
    data = [clean[clean[d.x] == c][d.y] for c in categories]
    parts = ax.violinplot(data, showmedians=True)
    for body in parts["bodies"]:
        body.set_facecolor(PRIMARY_COLOR)
        body.set_alpha(0.6)
    ax.set_xticks(range(1, len(categories) + 1))
    ax.set_xticklabels([str(c) for c in categories])
    ax.set_xlabel(d.x)
    ax.set_ylabel(d.y)
    ax.set_title(f"Distribution shape of {d.y} by {d.x}")
    _rotate_labels(ax)


def _render_stacked_bar(df, d, ax, fig):
    cat1, cat2 = d.x
    clean = df[[cat1, cat2, d.y]].dropna()
    pivot = clean.pivot_table(index=cat1, columns=cat2, values=d.y, aggfunc="mean", fill_value=0)
    pivot.plot(kind="bar", stacked=True, ax=ax, color=PALETTE)
    ax.set_xlabel(cat1)
    ax.set_ylabel(d.y)
    ax.set_title(f"{d.y} by {cat1} and {cat2}")
    _rotate_labels(ax)
    ax.legend(title=cat2, bbox_to_anchor=(1.05, 1), loc="upper left", frameon=False, fontsize=8)


def _render_correlation_heatmap(df, d, ax, fig):
    numeric_cols = d.x
    clean = df[numeric_cols].dropna()
    corr = clean.corr()
    im = ax.imshow(corr.values, cmap="coolwarm", vmin=-1, vmax=1)
    ax.set_xticks(range(len(numeric_cols)))
    ax.set_yticks(range(len(numeric_cols)))
    ax.set_xticklabels(numeric_cols, rotation=45, ha="right")
    ax.set_yticklabels(numeric_cols)
    ax.grid(False)
    for i in range(len(numeric_cols)):
        for j in range(len(numeric_cols)):
            v = corr.values[i, j]
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=8,
                     color="white" if abs(v) > 0.6 else "black")
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Correlation strength (-1 = opposite, +1 = same direction)", fontsize=8)
    ax.set_title("Correlation Heatmap")


def _render_scatter_matrix(df, d, ax, fig):
    numeric_cols = d.x
    clean = df[numeric_cols].dropna()
    plt.close(fig)
    size = 2.3 * len(numeric_cols)
    axes = pd.plotting.scatter_matrix(clean, figsize=(size, size), diagonal="hist",
                                       color=PRIMARY_COLOR, alpha=0.6,
                                       hist_kwds={"color": PRIMARY_COLOR})
    new_fig = axes[0, 0].get_figure()
    new_fig.suptitle("Pairwise Relationships Between Numeric Columns", y=1.02, fontweight="bold")
    return new_fig


def _rotate_labels(ax):
    ax.tick_params(axis="x", rotation=45)
    for label in ax.get_xticklabels():
        label.set_ha("right")


_RENDERERS = {
    "line": _render_line,
    "scatter": _render_scatter,
    "bar": _render_bar,
    "bar_count": _render_bar_count,
    "histogram": _render_histogram,
    "pie": _render_pie,
    "box": _render_box,
    "violin": _render_violin,
    "stacked_bar": _render_stacked_bar,
    "correlation_heatmap": _render_correlation_heatmap,
    "scatter_matrix": _render_scatter_matrix,
}


# --- What the chart shows (main caption, bold) --------------------------

_EXPLANATIONS = {
    "line": lambda d: f"This line chart tracks how '{d.y}' changes over '{d.x}'. Use it to spot trends, spikes, or drops over time.",
    "scatter": lambda d: f"Each dot compares '{d.x}' against '{d.y}' for one row of data. Use it to spot correlation or clusters between the two.",
    "bar": lambda d: f"Each bar shows the average '{d.y}' for a category in '{d.x}', limited to the top {BAR_TOP_N} by value.",
    "bar_count": lambda d: f"Each bar shows how many rows fall into each category of '{d.x}', limited to the top {BAR_TOP_N} most frequent.",
    "histogram": lambda d: f"This shows how values of '{d.x}' are distributed across their range.",
    "pie": lambda d: f"Each slice shows what share of the data belongs to each category of '{d.x}'.",
    "box": lambda d: f"Each box shows the spread of '{d.y}' for a category in '{d.x}'.",
    "violin": lambda d: f"Each shape shows the full distribution of '{d.y}' for a category in '{d.x}'.",
    "stacked_bar": lambda d: f"Each bar shows total '{d.y}' for a category in '{d.x[0]}', split into segments by '{d.x[1]}'.",
    "correlation_heatmap": lambda d: "Each cell shows how strongly two numeric columns move together.",
    "scatter_matrix": lambda d: "Each small chart compares two numeric columns at once; the diagonal shows each column's own distribution.",
}


# --- What each axis and color specifically means (second line, italic) --

_AXIS_COLOR_NOTES = {
    "line": lambda d: f"X-axis: {d.x} (chronological order). Y-axis: {d.y} (the measured value). Blue line/dots: the '{d.y}' value at each point in time; dots mark each actual data point.",
    "scatter": lambda d: f"X-axis: {d.x}. Y-axis: {d.y}. Each blue dot is one row of data; position shows its combination of both values. No categories are color-coded here.",
    "bar": lambda d: f"X-axis: {d.x} categories. Y-axis: average {d.y}. All bars are the same blue color since only one value is being measured — height alone carries the meaning.",
    "bar_count": lambda d: f"X-axis: {d.x} categories. Y-axis: number of rows (count), not a measured value. Bars are uniformly colored since only frequency is shown.",
    "histogram": lambda d: f"X-axis: {d.x} value ranges (bins). Y-axis: density (how concentrated values are). Blue bars: how many rows fall in each range; red line: a smoothed estimate of the overall shape.",
    "pie": lambda d: f"Each colored slice represents one category of '{d.x}' (see legend on the right for which color is which). Slice size and the percentage label show that category's share of the total.",
    "box": lambda d: f"X-axis: {d.x} categories. Y-axis: {d.y}. Box color is uniform (not meaningful); the box itself shows the middle 50% of values, the line inside is the median, and dots beyond the whiskers are outliers.",
    "violin": lambda d: f"X-axis: {d.x} categories. Y-axis: {d.y}. Shape width at any height shows how many values cluster there; the white marker is the median. Color is uniform, not category-coded.",
    "stacked_bar": lambda d: f"X-axis: {d.x[0]} categories. Y-axis: total {d.y}. Each color in the bar (see legend) represents one value of '{d.x[1]}' — segment height shows that subgroup's contribution to the total.",
    "correlation_heatmap": lambda d: "X-axis and Y-axis: the same list of numeric columns, forming a grid. Cell color follows the scale on the right: red shades mean a strong positive relationship, blue shades mean a strong negative one, near-white means little to no relationship.",
    "scatter_matrix": lambda d: "Each row and column corresponds to one numeric column. Off-diagonal charts plot two columns against each other (position shows their relationship); diagonal charts show one column's own value distribution. Color is uniform, not category-coded.",
}