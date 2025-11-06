"""Generate a simple report specification based on table profiles."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from .analysis import TableProfile
from .llm import NarrativeRefiner


@dataclass
class VisualSpec:
    """Specification of a single visual for a Power BI report."""

    title: str
    visual_type: str
    x_axis: Optional[str]
    y_axis: Optional[str]
    breakdown_by: Optional[str] = None
    summary: Optional[str] = None

    def as_dict(self) -> Dict[str, Optional[str]]:
        return {
            "title": self.title,
            "visual_type": self.visual_type,
            "x_axis": self.x_axis,
            "y_axis": self.y_axis,
            "breakdown_by": self.breakdown_by,
            "summary": self.summary,
        }


class ReportPlanner:
    """Generate Power BI report suggestions from table profiles."""

    def __init__(
        self,
        profile: TableProfile,
        *,
        narrative_refiner: Optional[NarrativeRefiner] = None,
    ) -> None:
        self.profile = profile
        self.narrative_refiner = narrative_refiner

    def plan(
        self,
        *,
        business_goals: Optional[str] = None,
    ) -> Dict[str, object]:
        visuals = self._recommend_visuals()
        summary = self._build_summary(visuals)
        plan: Dict[str, object] = {
            "table": self.profile.as_dict(),
            "visuals": [visual.as_dict() for visual in visuals],
            "narrative": summary,
        }

        if self.narrative_refiner:
            refined = self.narrative_refiner.refine_plan(
                plan,
                business_goals=business_goals,
            )
            if refined:
                plan = refined

        return plan

    def _recommend_visuals(self) -> List[VisualSpec]:
        visuals: List[VisualSpec] = []
        numeric_columns = [c for c in self.profile.column_profiles if c.numeric]
        categorical_columns = [c for c in self.profile.column_profiles if c.categorical]
        datetime_columns = [c for c in self.profile.column_profiles if c.datetime]

        # Prioritize time series if available
        if datetime_columns and numeric_columns:
            date_col = datetime_columns[0]
            metric = numeric_columns[0]
            visuals.append(
                VisualSpec(
                    title=f"{metric.name} over time",
                    visual_type="line_chart",
                    x_axis=date_col.name,
                    y_axis=metric.name,
                    summary=(
                        f"Trend of {metric.name} aggregated by {date_col.name}. Useful for spotting seasonal patterns."
                    ),
                )
            )

        # Category vs metric bar charts
        if categorical_columns and numeric_columns:
            category = categorical_columns[0]
            metric = numeric_columns[0]
            visuals.append(
                VisualSpec(
                    title=f"{metric.name} by {category.name}",
                    visual_type="column_chart",
                    x_axis=category.name,
                    y_axis=metric.name,
                    summary=(
                        f"Compares {metric.name} across the top values of {category.name}."
                    ),
                )
            )

        # Category breakdown with multiple metrics
        if len(numeric_columns) > 1 and categorical_columns:
            metric_a, metric_b = numeric_columns[:2]
            category = categorical_columns[0]
            visuals.append(
                VisualSpec(
                    title=f"{metric_a.name} vs {metric_b.name} by {category.name}",
                    visual_type="clustered_column_chart",
                    x_axis=category.name,
                    y_axis=metric_a.name,
                    breakdown_by=metric_b.name,
                    summary=(
                        f"Highlights the relationship between {metric_a.name} and {metric_b.name} grouped by {category.name}."
                    ),
                )
            )

        # KPI card for main metric
        if numeric_columns:
            metric = numeric_columns[0]
            visuals.append(
                VisualSpec(
                    title=f"Total {metric.name}",
                    visual_type="kpi_card",
                    x_axis=None,
                    y_axis=metric.name,
                    summary=f"Displays the overall value of {metric.name} as a KPI card.",
                )
            )

        # fallback table visual if little structure
        if not visuals:
            visuals.append(
                VisualSpec(
                    title="Data table",
                    visual_type="table",
                    x_axis=None,
                    y_axis=None,
                    summary="Raw data table for manual exploration.",
                )
            )

        return visuals

    def _build_summary(self, visuals: List[VisualSpec]) -> str:
        lines = [
            f"The dataset '{self.profile.name}' contains {self.profile.row_count} rows and {len(self.profile.column_profiles)} columns."
        ]

        numeric = [c.name for c in self.profile.column_profiles if c.numeric]
        categorical = [c.name for c in self.profile.column_profiles if c.categorical]

        if numeric:
            lines.append("Numeric fields: " + ", ".join(numeric) + ".")
        if categorical:
            lines.append("Categorical fields: " + ", ".join(categorical) + ".")

        if visuals:
            lines.append(
                "Recommended visuals include: "
                + "; ".join(f"{visual.visual_type} titled '{visual.title}'" for visual in visuals)
                + "."
            )

        return " ".join(lines)
