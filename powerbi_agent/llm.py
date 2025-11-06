"""LLM-powered refinement utilities for report plans."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Dict, List, Optional

import requests


class LLMError(RuntimeError):
    """Raised when an LLM refinement request fails."""


@dataclass
class NarrativeRefiner:
    """Refine report narratives and visuals using an LLM."""

    api_key: Optional[str] = None
    model: str = "gpt-4o-mini"
    endpoint: str = "https://api.openai.com/v1/chat/completions"
    timeout: int = 60

    def __post_init__(self) -> None:
        if self.api_key is None:
            self.api_key = os.getenv("OPENAI_API_KEY")

    def _build_prompt(
        self,
        plan: Dict[str, object],
        *,
        business_goals: Optional[str],
    ) -> List[Dict[str, str]]:
        plan_json = json.dumps(plan)
        goals_text = business_goals or "No specific goals provided. Focus on broad executive insights."
        system = (
            "You are a senior Power BI consultant. Improve report narratives, prioritising the listed business "
            "goals. Respond with strict JSON so it can be parsed by code."
        )
        user = (
            "Business goals: "
            + goals_text
            + "\n\nCurrent plan JSON:"
            + plan_json
            + "\n\nReturn JSON with keys 'narrative' (string) and 'visuals' (list of objects). "
            "Each item in 'visuals' must contain 'title'. Optionally include 'summary', 'visual_type', 'x_axis', "
            "'y_axis', and 'breakdown_by' if you recommend changes."
        )
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

    def refine_plan(
        self,
        plan: Dict[str, object],
        *,
        business_goals: Optional[str] = None,
    ) -> Optional[Dict[str, object]]:
        """Call the LLM to refine the narrative and visuals.

        Returns the updated plan if successful, otherwise ``None``.
        """

        if not self.api_key:
            return None

        payload = {
            "model": self.model,
            "response_format": {"type": "json_object"},
            "messages": self._build_prompt(plan, business_goals=business_goals),
        }

        response = requests.post(
            self.endpoint,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=self.timeout,
        )

        if response.status_code >= 300:
            raise LLMError(
                f"Failed to refine plan with LLM ({response.status_code}): {response.text}"
            )

        data = response.json()
        try:
            message_content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:  # pragma: no cover - defensive
            raise LLMError(f"Unexpected LLM response: {data}") from exc

        try:
            refinement = json.loads(message_content)
        except json.JSONDecodeError as exc:
            raise LLMError("LLM response was not valid JSON") from exc

        updated_plan: Dict[str, object] = dict(plan)
        if narrative := refinement.get("narrative"):
            updated_plan["narrative"] = narrative

        if "visuals" in refinement:
            updated_visuals = self._merge_visual_updates(
                plan.get("visuals", []),
                refinement.get("visuals", []),
            )
            updated_plan["visuals"] = updated_visuals

        return updated_plan

    @staticmethod
    def _merge_visual_updates(
        current_visuals: List[Dict[str, object]],
        updates: List[Dict[str, object]],
    ) -> List[Dict[str, object]]:
        visuals_by_title = {str(visual.get("title")): dict(visual) for visual in current_visuals}

        for update in updates:
            title = str(update.get("title"))
            if not title:
                continue
            existing = visuals_by_title.get(title, {})
            merged = {**existing}
            for key, value in update.items():
                if value is not None:
                    merged[key] = value
            visuals_by_title[title] = merged

        return list(visuals_by_title.values())
