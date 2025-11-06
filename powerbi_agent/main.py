"""Command line interface for generating Power BI report plans."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from .analysis import DataProfiler
from .excel_loader import ExcelDataLoader
from .llm import NarrativeRefiner, LLMError
from .powerbi_service import PowerBIReportDeployer, PowerBIService, PowerBIServiceError
from .report_planner import ReportPlanner


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a Power BI report plan from an Excel workbook",
    )
    parser.add_argument("excel_path", type=Path, help="Path to the Excel file to analyse")
    parser.add_argument(
        "--sheet",
        type=str,
        default=None,
        help="Optional sheet name within the workbook",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("report_plan.json"),
        help="Destination JSON file for the generated plan",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="Indentation level for the JSON output",
    )
    parser.add_argument(
        "--business-goals",
        type=str,
        default=None,
        help="Narrative focus areas passed to the LLM",
    )
    parser.add_argument(
        "--llm-model",
        type=str,
        default="gpt-4o-mini",
        help="LLM model identifier used for narrative refinement",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Disable LLM refinement even if an API key is available",
    )
    parser.add_argument(
        "--powerbi-group-id",
        type=str,
        default=None,
        help="Power BI workspace (group) identifier",
    )
    parser.add_argument(
        "--powerbi-dataset-name",
        type=str,
        default=None,
        help="Dataset name to create or reuse in Power BI",
    )
    parser.add_argument(
        "--powerbi-report-name",
        type=str,
        default=None,
        help="Report name to create in Power BI",
    )
    parser.add_argument(
        "--powerbi-access-token",
        type=str,
        default=None,
        help="Access token for authenticating with the Power BI REST API",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    loader = ExcelDataLoader(args.excel_path, sheet=args.sheet)
    table = loader.load()
    profile = DataProfiler.profile(table.name, table.dataframe)
    narrative_refiner = None

    if not args.no_llm:
        narrative_refiner = NarrativeRefiner(model=args.llm_model)

    planner = ReportPlanner(profile, narrative_refiner=narrative_refiner)

    try:
        plan: dict[str, Any] = planner.plan(business_goals=args.business_goals)
    except LLMError as exc:
        raise SystemExit(f"LLM refinement failed: {exc}")

    args.output.write_text(json.dumps(plan, indent=args.indent))
    print(f"Report plan saved to {args.output}")

    if args.powerbi_group_id and args.powerbi_report_name:
        access_token = args.powerbi_access_token or os.getenv("POWERBI_ACCESS_TOKEN")
        if not access_token:
            raise PowerBIServiceError("Power BI access token is required when deploying reports")
        dataset_name = args.powerbi_dataset_name or f"{table.name} Dataset"

        service = PowerBIService(access_token=access_token, group_id=args.powerbi_group_id)
        deployer = PowerBIReportDeployer(service)
        try:
            report = deployer.deploy(
                plan,
                dataset_name=dataset_name,
                report_name=args.powerbi_report_name,
            )
        except PowerBIServiceError as exc:
            raise SystemExit(f"Failed to create report via Power BI REST API: {exc}")

        print(
            f"Created report '{report.get('name')}' (ID: {report.get('id')}) in workspace {args.powerbi_group_id}"
        )


if __name__ == "__main__":
    main()
