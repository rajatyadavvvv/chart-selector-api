"""Handles dataset ingestion from a JSON payload in columns/rows format."""

import logging

import pandas as pd
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class DataLoadError(Exception):
    """Raised when a dataset cannot be loaded or parsed."""


class DatasetPayload(BaseModel):
    columns: list[str]
    rows: list[list]


def load_dataset(payload: DatasetPayload) -> pd.DataFrame:
    if not payload.columns:
        raise DataLoadError("The 'columns' list cannot be empty.")
    if not payload.rows:
        raise DataLoadError("The 'rows' list cannot be empty.")

    expected_len = len(payload.columns)
    for i, row in enumerate(payload.rows):
        if len(row) != expected_len:
            raise DataLoadError(
                f"Row {i} has {len(row)} values but there are {expected_len} columns."
            )

    try:
        df = pd.DataFrame(payload.rows, columns=payload.columns)
    except Exception as exc:
        logger.exception("Failed to build DataFrame from payload")
        raise DataLoadError(f"Could not construct a dataset from the payload: {exc}") from exc

    if df.empty:
        raise DataLoadError("The dataset contains no data.")

    logger.info("Loaded dataset from payload: %d rows, %d columns", *df.shape)
    return df