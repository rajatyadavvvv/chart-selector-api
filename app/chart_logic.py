"""Rule-based chart type selection based on column types and cardinality."""

import logging
from dataclasses import dataclass
from typing import Optional, Union

import pandas as pd

logger = logging.getLogger(__name__)

VIOLIN_MAX_CARDINALITY = 6
BOX_MAX_CARDINALITY = 20
STACKED_BAR_MAX_CARDINALITY = 10
PIE_MAX_CARDINALITY = 10
SCATTER_MATRIX_MAX_NUMERIC = 5
SCATTER_MATRIX_MIN_NUMERIC = 3


@dataclass
class ChartDecision:
    chart_type: str
    x: Union[str, list[str]]
    y: Optional[str] = None


def select_chart_type(df: pd.DataFrame) -> ChartDecision:
    df = _clean_dataframe(df)

    if df.shape[1] == 0:
        raise ValueError("No usable columns remain after cleaning the dataset.")

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    datetime_cols = _detect_datetime_columns(df, numeric_cols)
    categorical_cols = [c for c in df.columns if c not in numeric_cols and c not in datetime_cols]

    decision = (
        _rule_time_series(datetime_cols, numeric_cols)
        or _rule_correlation(numeric_cols)
        or _rule_scatter_matrix(numeric_cols)
        or _rule_stacked_bar(df, categorical_cols, numeric_cols)
        or _rule_categorical_numeric(df, categorical_cols, numeric_cols)
        or _rule_categorical_only(df, categorical_cols, numeric_cols)
        or _rule_scatter(numeric_cols)
        or _rule_histogram(numeric_cols)
        or _fallback(df)
    )

    logger.info("Selected chart: %s", decision)
    return decision


def _rule_time_series(datetime_cols, numeric_cols):
    if datetime_cols and numeric_cols:
        return ChartDecision("line", datetime_cols[0], numeric_cols[0])


def _rule_correlation(numeric_cols):
    if len(numeric_cols) > SCATTER_MATRIX_MAX_NUMERIC:
        return ChartDecision("correlation_heatmap", numeric_cols)


def _rule_scatter_matrix(numeric_cols):
    if SCATTER_MATRIX_MIN_NUMERIC <= len(numeric_cols) <= SCATTER_MATRIX_MAX_NUMERIC:
        return ChartDecision("scatter_matrix", numeric_cols)


def _rule_stacked_bar(df, categorical_cols, numeric_cols):
    low_card = [c for c in categorical_cols if df[c].nunique() <= STACKED_BAR_MAX_CARDINALITY]
    if len(low_card) >= 2 and numeric_cols:
        return ChartDecision("stacked_bar", low_card[:2], numeric_cols[0])


def _rule_categorical_numeric(df, categorical_cols, numeric_cols):
    if categorical_cols and numeric_cols:
        cat_col = _pick_best_categorical(df, categorical_cols)
        n = df[cat_col].nunique()
        if n <= VIOLIN_MAX_CARDINALITY:
            return ChartDecision("violin", cat_col, numeric_cols[0])
        elif n <= BOX_MAX_CARDINALITY:
            return ChartDecision("box", cat_col, numeric_cols[0])
        else:
            return ChartDecision("bar", cat_col, numeric_cols[0])


def _rule_categorical_only(df, categorical_cols, numeric_cols):
    if categorical_cols and not numeric_cols:
        cat_col = _pick_best_categorical(df, categorical_cols)
        if df[cat_col].nunique() <= PIE_MAX_CARDINALITY:
            return ChartDecision("pie", cat_col)
        return ChartDecision("bar_count", cat_col)


def _rule_scatter(numeric_cols):
    if len(numeric_cols) == 2:
        return ChartDecision("scatter", numeric_cols[0], numeric_cols[1])


def _rule_histogram(numeric_cols):
    if len(numeric_cols) == 1:
        return ChartDecision("histogram", numeric_cols[0])


def _fallback(df):
    cols = df.columns.tolist()
    return ChartDecision("bar_count", cols[0])


def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].astype(str).str.strip()
        df[col] = df[col].replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})
    return df.dropna(axis=1, how="all")


def _detect_datetime_columns(df, numeric_cols):
    datetime_cols = df.select_dtypes(include="datetime").columns.tolist()
    if datetime_cols:
        return datetime_cols
    for col in df.select_dtypes(include="object").columns:
        if col in numeric_cols:
            continue
        try:
            pd.to_datetime(df[col], errors="raise")
            datetime_cols.append(col)
        except (ValueError, TypeError):
            continue
    return datetime_cols


def _pick_best_categorical(df, categorical_cols, max_unique: int = 50):
    candidates = [c for c in categorical_cols if df[c].nunique() <= max_unique]
    pool = candidates or categorical_cols
    return min(pool, key=lambda c: df[c].nunique())