"""Completion gate for ingredient Knowledge Objects.

Catalog size is not catalog readiness.  A KO is operational only when its
family and form resolve to instructions that expose outcomes, hazards, and
recovery—not merely a name and a generic cooking verb.
"""

from dataclasses import dataclass, field
import re

from config import DB_PATH
from ko_behavior import ResolvedBehavior, resolve_behavior


GENERIC_LANGUAGE = (
    re.compile(r"\bprep\s+[^.!?]+[.!?]?$", re.I),
    re.compile(r"\b(?:cook|heat|add)\b.*\buntil ready\b", re.I),
    re.compile(r"\bcook as directed\b", re.I),
)

# These are the 18 ingredient/method safety gates that must be satisfied before
# a route can be advertised as operational.  They are deliberately executable:
# release tests can name the exact missing dimension instead of treating
# "classified" as equivalent to "ready to cook."
SAFETY_GATES = (
    "classification",
    "form_route",
    "environment",
    "equipment",
    "timing",
    "attention",
    "stage",
    "handling",
    "operation",
    "outcome",
    "doneness",
    "failure_mode",
    "recovery",
    "holdability",
    "portion_model",
    "form_match",
    "frozen_handling",
    "raw_protein_endpoint",
)


@dataclass
class ContractReport:
    ingredient_name: str
    role: str
    form_name: str
    strategy: str
    family_codes: list[str] = field(default_factory=list)
    source: str = "unclassified"
    status: str = "untrained"
    missing: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checks: dict[str, bool] = field(default_factory=dict)

    @property
    def operational(self):
        return self.status == "operational"


def _is_generic(text):
    value = str(text or "").strip()
    return not value or any(pattern.search(value) for pattern in GENERIC_LANGUAGE)


def _form_matches(form_name, method_forms):
    requested = str(form_name or "").strip().lower().replace("-", " ")
    supported = {
        str(value or "").strip().lower().replace("-", " ")
        for value in method_forms
    }
    if not requested or not supported or requested in supported:
        return True
    aliases = {
        "dry": {"dried", "shelf stable"},
        "dried": {"dry", "shelf stable"},
        "shelf stable": {"dry", "dried"},
    }
    return bool(aliases.get(requested, set()) & supported)


def audit_behavior(name, role, form_name="", strategy="", db_path=None):
    resolved: ResolvedBehavior = resolve_behavior(
        name, role, form_name, strategy, db_path or DB_PATH
    )
    report = ContractReport(
        name, role, form_name, strategy, resolved.family_codes, resolved.source
    )
    family = resolved.primary_family
    rule = resolved.method
    form_key = str(form_name or "").strip().lower().replace("-", " ")
    raw_protein = role == "protein" and family and family.code != "plant_protein" and any(
        word in form_key for word in ("raw", "fresh", "frozen")
    ) and not any(word in form_key for word in ("cooked", "ready to eat", "canned"))
    frozen = "frozen" in form_key
    checks = {gate: False for gate in SAFETY_GATES}
    checks["classification"] = bool(family and resolved.family_codes)
    checks["form_route"] = bool(rule)
    if not family:
        report.missing.append("verified behavior-family classification")
    if family and not rule:
        report.missing.append("form- and environment-compatible method")
        if resolved.incompatibility_reason:
            report.warnings.append(resolved.incompatibility_reason)
    if rule:
        checks.update({
            "environment": bool(str(rule.environment or "").strip() and str(rule.creates_environment or "").strip()),
            "equipment": bool(str(rule.equipment or "").strip()),
            "timing": (
                isinstance(rule.prep_minutes, int)
                and isinstance(rule.cook_minutes, int)
                and isinstance(rule.active_minutes, int)
                and rule.prep_minutes >= 0
                and rule.cook_minutes >= 0
                and 0 <= rule.active_minutes <= rule.prep_minutes + rule.cook_minutes
            ),
            "attention": 0 <= float(rule.attention_load) <= 1,
            "stage": rule.stage in {"early", "middle", "late", "finish"},
            "handling": not _is_generic(rule.handling_template),
            "operation": not _is_generic(rule.instruction_template),
            "outcome": bool(str(rule.desired_outcome or "").strip()),
            "doneness": bool(str(rule.doneness_cue or "").strip()),
            "failure_mode": bool(str(rule.failure_mode or "").strip()),
            "recovery": bool(str(rule.recovery_hint or "").strip()),
            "holdability": rule.holdability in {"poor", "fair", "good", "excellent"},
            "portion_model": bool(
                family
                and str(family.portion_basis or "").strip()
                and float(family.portion_per_standard) > 0
                and str(family.portion_label or "").strip()
                and str(family.portion_rounding or "").strip()
            ),
            "form_match": _form_matches(form_name, rule.forms),
            "frozen_handling": (
                not frozen
                or bool(rule.frozen_thaw_template)
                or "thaw" in str(rule.handling_template or "").lower()
                or any("frozen" in str(value or "").lower() for value in rule.forms)
            ),
        })
        cue = str(rule.doneness_cue or "").lower()
        checks["raw_protein_endpoint"] = (
            not raw_protein
            or any(token in cue for token in ("°f", "opaque", "no raw", "safely cooked"))
        )
        required = {
            "cooking environment": rule.environment,
            "created environment": rule.creates_environment,
            "handling instruction": rule.handling_template,
            "operation instruction": rule.instruction_template,
            "desired outcome": rule.desired_outcome,
            "observable doneness cue": rule.doneness_cue,
            "failure mode": rule.failure_mode,
            "recovery guidance": rule.recovery_hint,
            "holdability": rule.holdability,
        }
        report.missing.extend(label for label, value in required.items() if not str(value or "").strip())
        if _is_generic(rule.handling_template):
            report.missing.append("specific handling instruction")
        if _is_generic(rule.instruction_template):
            report.missing.append("specific operation instruction")
        if raw_protein:
            if not any(token in cue for token in ("°f", "opaque", "no raw", "safely cooked")):
                report.missing.append("raw-protein safety endpoint")
        report.missing.extend(
            f"safety gate: {gate.replace('_', ' ')}"
            for gate, passed in checks.items()
            if not passed
        )
    report.checks = checks
    report.missing = list(dict.fromkeys(report.missing))
    report.status = "operational" if not report.missing else (
        "conditional" if family else "untrained"
    )
    return report
