"""Integration with the Power BI REST API."""

from __future__ import annotations

import json
from typing import Dict, Iterable, List, Optional

import requests


class PowerBIServiceError(RuntimeError):
    """Raised when communication with the Power BI API fails."""


class PowerBIService:
    """Thin wrapper around the Power BI REST API."""

    def __init__(self, access_token: str, group_id: str) -> None:
        self.group_id = group_id
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }
        )

    # Dataset helpers -------------------------------------------------
    def list_datasets(self) -> List[Dict[str, object]]:
        response = self.session.get(
            f"https://api.powerbi.com/v1.0/myorg/groups/{self.group_id}/datasets"
        )
        self._ensure_success(response)
        return response.json().get("value", [])

    def create_push_dataset(
        self,
        *,
        dataset_name: str,
        table_schema: Dict[str, object],
    ) -> str:
        payload = {
            "name": dataset_name,
            "defaultMode": "Push",
            "tables": [table_schema],
        }
        response = self.session.post(
            f"https://api.powerbi.com/v1.0/myorg/groups/{self.group_id}/datasets",
            data=json.dumps(payload),
        )
        self._ensure_success(response, expected_codes={200, 201})
        return response.json()["id"]

    def get_or_create_dataset(
        self,
        *,
        dataset_name: str,
        table_schema: Dict[str, object],
    ) -> str:
        for dataset in self.list_datasets():
            if dataset.get("name") == dataset_name:
                return str(dataset["id"])
        return self.create_push_dataset(dataset_name=dataset_name, table_schema=table_schema)

    # Report helpers --------------------------------------------------
    def create_report(
        self,
        *,
        dataset_id: str,
        report_name: str,
        layout: Dict[str, object],
    ) -> Dict[str, object]:
        payload = {
            "name": report_name,
            "datasetId": dataset_id,
            "definition": layout,
        }
        response = self.session.post(
            f"https://api.powerbi.com/v1.0/myorg/groups/{self.group_id}/reports",
            data=json.dumps(payload),
        )
        self._ensure_success(response, expected_codes={200, 201})
        return response.json()

    # Utilities -------------------------------------------------------
    @staticmethod
    def _ensure_success(response: requests.Response, expected_codes: Optional[Iterable[int]] = None) -> None:
        if expected_codes is None:
            expected_codes = {200}
        if response.status_code not in expected_codes:
            raise PowerBIServiceError(
                f"Power BI API call failed ({response.status_code}): {response.text}"
            )


class PowerBIReportDeployer:
    """Translate report plans into API calls that create a Power BI report."""

    def __init__(self, service: PowerBIService) -> None:
        self.service = service

    def deploy(
        self,
        plan: Dict[str, object],
        *,
        dataset_name: str,
        report_name: str,
    ) -> Dict[str, object]:
        table = plan["table"]
        schema = self._build_table_schema(table)
        dataset_id = self.service.get_or_create_dataset(
            dataset_name=dataset_name,
            table_schema=schema,
        )
        layout = self._build_report_layout(plan, dataset_id)
        return self.service.create_report(
            dataset_id=dataset_id,
            report_name=report_name,
            layout=layout,
        )

    def _build_table_schema(self, table: Dict[str, object]) -> Dict[str, object]:
        columns = []
        for column in table.get("columns", []):
            data_type = self._map_powerbi_type(column)
            columns.append({"name": column["name"], "dataType": data_type})
        return {
            "name": table.get("name", "AutoDataset"),
            "columns": columns,
        }

    def _build_report_layout(self, plan: Dict[str, object], dataset_id: str) -> Dict[str, object]:
        visuals = []
        for index, visual in enumerate(plan.get("visuals", [])):
            visuals.append(
                self._visual_to_container(
                    visual,
                    dataset_id=dataset_id,
                    table_name=plan["table"].get("name", "AutoDataset"),
                    order=index,
                )
            )

        return {
            "pages": [
                {
                    "name": "ReportSection",
                    "displayName": "Overview",
                    "visualContainers": visuals,
                }
            ]
        }

    def _visual_to_container(
        self,
        visual: Dict[str, object],
        *,
        dataset_id: str,
        table_name: str,
        order: int,
    ) -> Dict[str, object]:
        def projection(field_name: Optional[str]) -> Optional[List[Dict[str, str]]]:
            if not field_name:
                return None
            return [
                {
                    "queryRef": field_name,
                    "source": {
                        "entity": table_name,
                        "column": field_name,
                        "datasetId": dataset_id,
                    },
                }
            ]

        config = {
            "name": visual.get("title", f"Visual{order}"),
            "position": {
                "x": (order % 2) * 0.5,
                "y": (order // 2) * 0.5,
                "z": 0,
                "width": 0.48,
                "height": 0.48,
            },
            "config": {
                "singleVisual": {
                    "visualType": visual.get("visual_type", "table"),
                    "projections": {
                        "Values": projection(visual.get("y_axis")) or [],
                        "Category": projection(visual.get("x_axis")) or [],
                        "Series": projection(visual.get("breakdown_by")) or [],
                    },
                    "subtitle": visual.get("summary"),
                }
            },
        }

        return config

    @staticmethod
    def _map_powerbi_type(column: Dict[str, object]) -> str:
        if column.get("numeric"):
            return "Double"
        if column.get("datetime"):
            return "DateTime"
        return "String"
