"""
Policy Engine for Skill-Broker.

Evaluates health values against configurable rules to determine
capability state changes.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from aas_contract import CAPABILITY_ELEMENT_PATHS

logger = logging.getLogger(__name__)


@dataclass
class PolicyAction:
    """Action to be taken when a policy rule matches."""

    path: str   # Submodel element path
    value: str  # New value to set


@dataclass
class PolicyRule:
    """A single policy rule with condition and actions."""

    condition: str       # e.g., "health < 90"
    actions: list[PolicyAction]
    priority: int = 0    # Higher priority rules evaluated first


class PolicyEngine:
    """
    Evaluates health values against policy rules.

    Rule syntax example:
    ```yaml
    rules:
      - when: "health < 90"
        priority: 1
        actions:
          - path: "Capabilities/ProcessCapability:Milling/SurfaceFinishGrade"
            value: "B"
          - path: "Capabilities/ProcessCapability:Milling/AssuranceState"
            value: "offered"
    ```
    """

    def __init__(self, policy_file: str | None = None) -> None:
        self._rules: list[PolicyRule] = []

        if policy_file:
            self.load_from_file(policy_file)
        else:
            self._load_default_rules()

    def load_from_file(self, path: str) -> None:
        """Load policy rules from YAML file."""
        policy_path = Path(path)
        if not policy_path.exists():
            logger.warning(f"Policy file not found: {path}, using defaults")
            self._load_default_rules()
            return

        try:
            with policy_path.open() as f:
                data = yaml.safe_load(f)

            self._rules = []
            for rule_data in data.get("rules", []):
                actions = [
                    PolicyAction(path=a["path"], value=str(a["value"]))
                    for a in rule_data.get("actions", [])
                ]
                rule = PolicyRule(
                    condition=rule_data.get("when", ""),
                    actions=actions,
                    priority=rule_data.get("priority", 0),
                )
                self._rules.append(rule)

            # Sort by priority (highest first)
            self._rules.sort(key=lambda r: r.priority, reverse=True)
            logger.info(f"Loaded {len(self._rules)} policy rules from {path}")

        except Exception as e:
            logger.error(f"Failed to load policy file: {e}")
            self._load_default_rules()

    def _load_default_rules(self) -> None:
        """Load default policy rules."""
        self._rules = [
            # Severe degradation (health < 80)
            PolicyRule(
                condition="health < 80",
                priority=10,
                actions=[
                    PolicyAction(
                        path=CAPABILITY_ELEMENT_PATHS["assurance_state"],
                        value="notAvailable",
                    ),
                    PolicyAction(
                        path=CAPABILITY_ELEMENT_PATHS["surface_finish"],
                        value="C",
                    ),
                    PolicyAction(
                        path=CAPABILITY_ELEMENT_PATHS["tolerance_class"],
                        value="±0.05mm",
                    ),
                    PolicyAction(
                        path=CAPABILITY_ELEMENT_PATHS["energy_cost"],
                        value="1.25",
                    ),
                ],
            ),
            # Moderate degradation (health < 90)
            PolicyRule(
                condition="health < 90",
                priority=5,
                actions=[
                    PolicyAction(
                        path=CAPABILITY_ELEMENT_PATHS["assurance_state"],
                        value="offered",
                    ),
                    PolicyAction(
                        path=CAPABILITY_ELEMENT_PATHS["surface_finish"],
                        value="B",
                    ),
                    PolicyAction(
                        path=CAPABILITY_ELEMENT_PATHS["energy_cost"],
                        value="1.0",
                    ),
                ],
            ),
            # Healthy state (health >= 90)
            PolicyRule(
                condition="health >= 90",
                priority=1,
                actions=[
                    PolicyAction(
                        path=CAPABILITY_ELEMENT_PATHS["assurance_state"],
                        value="assured",
                    ),
                    PolicyAction(
                        path=CAPABILITY_ELEMENT_PATHS["surface_finish"],
                        value="A",
                    ),
                    PolicyAction(
                        path=CAPABILITY_ELEMENT_PATHS["tolerance_class"],
                        value="±0.02mm",
                    ),
                    PolicyAction(
                        path=CAPABILITY_ELEMENT_PATHS["energy_cost"],
                        value="0.85",
                    ),
                ],
            ),
        ]
        logger.info("Loaded default policy rules")

    def evaluate(self, health_index: int) -> list[PolicyAction]:
        """
        Evaluate health value against policy rules.

        Returns actions from the first matching rule (highest priority).
        """
        for rule in self._rules:
            if self._check_condition(rule.condition, health_index):
                logger.debug(f"Rule matched: {rule.condition}")
                return rule.actions

        return []

    def _check_condition(self, condition: str, health: int) -> bool:
        """
        Evaluate a simple condition expression.

        Supports: "health < X", "health > X", "health <= X", "health >= X", "health == X"
        """
        # Simple parser for conditions like "health < 90"
        condition = condition.strip().lower()

        if "<=" in condition:
            threshold = int(condition.split("<=")[1].strip())
            return health <= threshold
        elif ">=" in condition:
            threshold = int(condition.split(">=")[1].strip())
            return health >= threshold
        elif "<" in condition:
            threshold = int(condition.split("<")[1].strip())
            return health < threshold
        elif ">" in condition:
            threshold = int(condition.split(">")[1].strip())
            return health > threshold
        elif "==" in condition:
            threshold = int(condition.split("==")[1].strip())
            return health == threshold

        logger.warning(f"Unknown condition format: {condition}")
        return False

    def get_rules(self) -> list[dict[str, Any]]:
        """Get rules as serializable dictionaries."""
        return [
            {
                "condition": r.condition,
                "priority": r.priority,
                "actions": [{"path": a.path, "value": a.value} for a in r.actions],
            }
            for r in self._rules
        ]
