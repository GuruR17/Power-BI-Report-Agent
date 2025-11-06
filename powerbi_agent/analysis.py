"""Data profiling utilities used by the report planner."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import pandas as pd


@dataclass
class ColumnProfile:
    """Summary statistics about a column."""

    name: str
    dtype: str
    unique_values: int
    null_fraction: float
    numeric: bool
    categorical: bool
    datetime: bool


@dataclass
class TableProfile:
    """Profile summary for a complete table."""

    name: str
    row_count: int
    column_profiles: List[ColumnProfile]

    def as_dict(self) -> Dict[str, object]:
        return {
            "name": self.name,
            "row_count": self.row_count,
            "columns": [profile.__dict__ for profile in self.column_profiles],
        }


class DataProfiler:
    """Build lightweight profiles describing tabular data."""

    @staticmethod
    def profile(table_name: str, dataframe: pd.DataFrame) -> TableProfile:
        profiles: List[ColumnProfile] = []
        row_count = len(dataframe)

        for column in dataframe.columns:
            series = dataframe[column]
            dtype = str(series.dtype)
            unique_values = int(series.nunique(dropna=True))
            null_fraction = float(series.isna().mean())

            numeric = pd.api.types.is_numeric_dtype(series)
            datetime = pd.api.types.is_datetime64_any_dtype(series)

            # treat categoricals as anything with limited cardinality or explicit dtype
            categorical = (
                pd.api.types.is_categorical_dtype(series)
                or (not numeric and not datetime)
                or unique_values <= max(20, int(0.05 * row_count))
            )

            profiles.append(
                ColumnProfile(
                    name=str(column),
                    dtype=dtype,
                    unique_values=unique_values,
                    null_fraction=null_fraction,
                    numeric=numeric,
                    categorical=categorical,
                    datetime=datetime,
                )
            )

        return TableProfile(name=table_name, row_count=row_count, column_profiles=profiles)
