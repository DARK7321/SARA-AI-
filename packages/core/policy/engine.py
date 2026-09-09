"""Deterministic Policy Engine for OmniBrain.

Evaluates every proposed action against security rules, autonomy levels,
and budget constraints before execution occurs.
"""
from enum import Enum
import os
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
import yaml

from packages.connectors._sdk.contract import SideEffectType


class PolicyEffect(str, Enum):
    ALLOW = "ALLOW"
    CONFIRM = "CONFIRM"
    DENY = "DENY"


class PolicyDecisionResult(BaseModel):
    effect: PolicyEffect
    rule_id: str
    reason: str
    autonomy_level: int = 2


class PolicyEngine:
    """Evaluates proposed actions against deterministic security rules."""

    def __init__(self, config_path: str = "config/policies.yaml"):
        self.config_path = config_path
        self.rules: List[Dict[str, Any]] = []
        self.default_autonomy_level: int = 2
        self.load_rules()

    def load_rules(self) -> None:
        """Load rules from configuration file."""
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                self.rules = data.get("rules", [])
                self.default_autonomy_level = data.get("default_autonomy_level", 2)
        else:
            self.rules = []
            self.default_autonomy_level = 2

    def evaluate(
        self,
        action: str,
        side_effect: SideEffectType,
        risk_level: str = "LOW",
        budget_exceeded: bool = False,
        autonomy_level: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
        kill_switch_active: bool = False,
    ) -> PolicyDecisionResult:
        """Deterministically evaluate action authorization across Autonomy Levels 0 to 4."""
        level = autonomy_level if autonomy_level is not None else self.default_autonomy_level

        # 0. Emergency Kill Switch: Immediate system-wide lockdown
        if kill_switch_active:
            return PolicyDecisionResult(
                effect=PolicyEffect.DENY,
                rule_id="deny_emergency_kill_switch",
                reason="Operation denied: EMERGENCY KILL SWITCH IS ACTIVE. All autonomous execution is locked down.",
                autonomy_level=level,
            )

        # 1. Hard Budget Guard: Always DENY if budget cap is breached
        if budget_exceeded:
            return PolicyDecisionResult(
                effect=PolicyEffect.DENY,
                rule_id="deny_over_budget",
                reason="Operation denied: daily or task budget limit exceeded.",
                autonomy_level=level,
            )

        # 2. Level 0 Autonomy: Strict Manual - Nothing executes without confirmation
        if level == 0:
            return PolicyDecisionResult(
                effect=PolicyEffect.CONFIRM,
                rule_id="level_0_strict_approval",
                reason="Autonomy Level 0 requires explicit human confirmation for all actions.",
                autonomy_level=level,
            )

        # 3. Check configured rules in sequence
        for rule in self.rules:
            rule_id = rule.get("id", "custom_rule")

            # At Level 4 (Full Autonomous): all approval rules are bypassed except budget
            if level == 4 and rule_id != "deny_over_budget":
                continue

            # At Level 3 (Auto-Low-Risk): routine external sends are permitted autonomously
            if level >= 3 and rule_id == "deny_external_send_without_approval":
                continue

            condition = rule.get("condition", {})
            rule_effect = PolicyEffect(rule.get("effect", "CONFIRM"))
            rule_desc = rule.get("description", "Policy rule applied.")

            # Match side_effect condition
            if "side_effect" in condition:
                expected_effects = condition["side_effect"]
                if not isinstance(expected_effects, list):
                    expected_effects = [expected_effects]

                if side_effect.value in expected_effects or side_effect in expected_effects:
                    return PolicyDecisionResult(
                        effect=rule_effect,
                        rule_id=rule_id,
                        reason=rule_desc,
                        autonomy_level=level,
                    )

        # 4. Default Autonomy Fallbacks
        # Read-only actions are ALLOW for Level 1+
        if side_effect in (SideEffectType.NONE, SideEffectType.READ):
            return PolicyDecisionResult(
                effect=PolicyEffect.ALLOW,
                rule_id="default_read_allow",
                reason="Read-only and pure computation actions are automatically allowed.",
                autonomy_level=level,
            )

        # In Level 1: All mutations require confirmation
        if level <= 1:
            return PolicyDecisionResult(
                effect=PolicyEffect.CONFIRM,
                rule_id="level_1_mutation_confirm",
                reason="Action modifies external state and requires confirmation at Autonomy Level 1.",
                autonomy_level=level,
            )

        # In Level 2 (Default / Guarded): External sends, deletions, and HIGH/CRITICAL risk require confirmation
        if level == 2:
            if side_effect in (SideEffectType.DESTRUCTIVE, SideEffectType.EXTERNAL_SEND) or risk_level in ("HIGH", "CRITICAL"):
                return PolicyDecisionResult(
                    effect=PolicyEffect.CONFIRM,
                    rule_id="level_2_safe_confirm",
                    reason=f"Action '{action}' is {side_effect.value} with risk {risk_level}, requiring confirmation.",
                    autonomy_level=level,
                )
            return PolicyDecisionResult(
                effect=PolicyEffect.ALLOW,
                rule_id="level_2_safe_write_allow",
                reason=f"Action '{action}' is safe for autonomous execution under Level 2.",
                autonomy_level=level,
            )

        # In Level 3 (Auto-Low-Risk): Safe writes and routine external sends ALLOW; DESTRUCTIVE or CRITICAL confirm
        if level == 3:
            if side_effect == SideEffectType.DESTRUCTIVE or risk_level == "CRITICAL":
                return PolicyDecisionResult(
                    effect=PolicyEffect.CONFIRM,
                    rule_id="level_3_destructive_confirm",
                    reason=f"Action '{action}' is destructive or critical risk, requiring confirmation under Level 3.",
                    autonomy_level=level,
                )
            return PolicyDecisionResult(
                effect=PolicyEffect.ALLOW,
                rule_id="level_3_autonomous_allow",
                reason=f"Action '{action}' is approved for autonomous execution under Level 3.",
                autonomy_level=level,
            )

        # In Level 4 (Full Autonomous): All operations ALLOW up to budget limit
        return PolicyDecisionResult(
            effect=PolicyEffect.ALLOW,
            rule_id="level_4_full_autonomous_allow",
            reason=f"Action '{action}' is fully authorized under Autonomous Level 4.",
            autonomy_level=level,
        )

