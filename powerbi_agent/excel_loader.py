"""Loaders for Excel data sources."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import pandas as pd


@dataclass
class ExcelTable:
    """Represents a named table inside an Excel workbook."""

    name: str
    dataframe: pd.DataFrame


class ExcelDataLoader:
    """Read Excel workbooks into :class:`pandas.DataFrame` objects.

    Parameters
    ----------
    path:
        Path to the Excel file.
    sheet:
        Optional sheet name. When omitted the first sheet is used.
    header:
        Row index to use for the header row. Defaults to ``0`` (first row).
    """

    def __init__(self, path: str | Path, sheet: Optional[str] = None, header: int = 0):
        self.path = Path(path)
        self.sheet = sheet
        self.header = header

    def load(self) -> ExcelTable:
        """Load the configured Excel sheet.

        Returns
        -------
        ExcelTable
            Named tuple describing the sheet contents.
        """

        if not self.path.exists():
            raise FileNotFoundError(f"Excel file '{self.path}' does not exist")

        dataframe = pd.read_excel(self.path, sheet_name=self.sheet, header=self.header)
        sheet_name = self.sheet or dataframe.attrs.get("sheet_name") or "Sheet1"
        return ExcelTable(name=str(sheet_name), dataframe=dataframe)

    def available_sheets(self) -> List[str]:
        """Return the list of sheet names present in the workbook."""

        with pd.ExcelFile(self.path) as workbook:
            return list(workbook.sheet_names)
