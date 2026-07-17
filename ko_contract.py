"""Completion gate for ingredient Knowledge Objects.

Catalog size is not catalog readiness.  A KO is operational only when its
family and form resolve to instructions that expose outcomes, hazards, and
recovery—not merely a name and a generic cooking verb.
"""

from dataclasses import dataclass, field
import re

from ko_behavior import ResolvedBehavior, resolve_behavior


GENERIC_LANGUAGE = (
    re.compile(r"\bprep\s+[^.!?]+[.!?]?$", re.I),
    re.compile(r"\b(?:cook|heat|add)\b.*\buntil ready\b", re.I),
    re.compile(r"\bcook as directed\b", re.I),
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

    @property
    def operational(self):
        return self.status == "operational"


def _is_generic(text):
    value = str(text or "").strip()
    return not value or any(pattern.search(value) for pattern in GENERIC_LANGUAGE)


def audit_behavior(name, role, form_name="", strategy="", db_path=None):
    resolved: ResolvedBehavior = resolve_behavior(
        name, role, form_name, strategy, db_path
    )
    report = ContractReport(
        name, role, form_name, strategy, resolved.family_codes, resolved.source
    )
    family = resolved.primary_family
    rule = resolved.method
    if not family:
        report.missing.append("verified behavior-family classification")
    if family and not rule:
        report.missing.append("form- and environment-compatible method")
        if resolved.incompatibility_reason:
            report.warnings.append(resolved.incompatibility_reason)
    if rule:
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
        if role == "protein" and any(word in form_name.lower() for word in ("raw", "fresh", "frozen")):
            cue = rule.doneness_cue.lower()
            if not any(token in cue for token in ("°f", "opaque", "no raw", "safely cooked")):
                report.missing.append("raw-protein safety endpoint")
    report.missing = list(dict.fromkeys(report.missing))
    report.status = "operational" if not report.missing else (
        "conditional" if family else "untrained"
    )
    return report
