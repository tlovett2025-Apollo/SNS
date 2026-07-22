"""Batch learning, enrichment, promotion, and release policy for SNS."""

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import re


def _clean(value) -> str:
    return " ".join(str(value or "").strip().split())


def _key(value) -> str:
    return re.sub(r"[^a-z0-9]+", " ", _clean(value).lower()).strip()


ISSUE_ROUTING = {
    "wrong_ingredients": ("component_identity", 4),
    "weird_instructions": ("behavior_execution", 3),
    "uncookable_combination": ("meal_coherence", 5),
    "timing_or_effort": ("meal_orchestration", 3),
    "wrong_quantity": ("quantity_contract", 3),
    "general_review": ("human_review", 2),
    "recipe_ok": ("positive_evidence", 0),
}


@dataclass(frozen=True)
class LearningCluster:
    fingerprint: str
    route: str
    category: str
    count: int
    severity: int
    candidate_ids: tuple[str, ...]
    build_ids: tuple[str, ...]
    status: str


def cluster_recipe_reports(reports: list[dict], recurrence_threshold=2) -> list[dict]:
    """Group repeated symptoms by architecture layer, method, and meal family."""
    buckets = defaultdict(list)
    for report in reports or []:
        snapshot = report.get("recipe_snapshot") or report.get("p_recipe_snapshot") or {}
        categories = report.get("issue_categories") or report.get("p_issue_categories") or ["general_review"]
        for category in categories:
            route, severity = ISSUE_ROUTING.get(category, ISSUE_ROUTING["general_review"])
            method = _key(snapshot.get("cooking_method") or snapshot.get("production_strategy")) or "unknown method"
            family = _key(snapshot.get("dish_family") or snapshot.get("meal_structure")) or "unknown family"
            fingerprint = f"{route}:{method}:{family}"
            buckets[fingerprint].append((report, category, route, severity))

    clusters = []
    for fingerprint, rows in buckets.items():
        reports_only = [row[0] for row in rows]
        category, route, severity = rows[0][1:]
        count = len(rows)
        candidate_ids = tuple(sorted({
            _clean(item.get("candidate_id") or item.get("p_candidate_id"))
            for item in reports_only if _clean(item.get("candidate_id") or item.get("p_candidate_id"))
        }))
        build_ids = tuple(sorted({
            _clean(item.get("build_id") or item.get("p_build_id"))
            for item in reports_only if _clean(item.get("build_id") or item.get("p_build_id"))
        }))
        clusters.append(asdict(LearningCluster(
            fingerprint, route, category, count, severity,
            candidate_ids, build_ids,
            "batch_review" if count >= recurrence_threshold else "observe",
        )))
    return sorted(clusters, key=lambda item: (-item["severity"], -item["count"], item["fingerprint"]))


def build_enrichment_queue(clusters=None, retail_drafts=None, unmatched_items=None) -> list[dict]:
    queue = []
    for cluster in clusters or []:
        if cluster.get("route") == "positive_evidence":
            continue
        queue.append({
            "queue_type": "behavior_learning",
            "key": cluster["fingerprint"],
            "priority": int(cluster.get("severity") or 0) * 100 + int(cluster.get("count") or 0) * 10,
            "evidence_count": int(cluster.get("count") or 0),
            "required_action": "review_cluster_then_add_or_correct_declarative_knowledge",
            "promotion_status": "not_ready",
        })
    for draft in retail_drafts or []:
        product = draft.get("retail_product") or draft
        queue.append({
            "queue_type": "retail_product",
            "key": _clean(product.get("barcode") or product.get("product_name")),
            "priority": 120,
            "evidence_count": 1,
            "required_action": "confirm_identity_and_directions",
            "promotion_status": "not_ready",
        })
    counts = Counter(_key(item.get("name") if isinstance(item, dict) else item) for item in unmatched_items or [])
    for name, count in counts.items():
        if name:
            queue.append({
                "queue_type": "ingredient_identity", "key": name,
                "priority": 80 + count * 10, "evidence_count": count,
                "required_action": "resolve_canonical_identity", "promotion_status": "not_ready",
            })
    return sorted(queue, key=lambda item: (-item["priority"], item["queue_type"], item["key"]))


PROMOTION_REQUIREMENTS = (
    "canonical_identity_confirmed", "provenance_present",
    "safety_reviewed", "behavior_contract_complete", "regression_cases",
)


def promotion_decision(evidence: dict) -> dict:
    missing = []
    for field in PROMOTION_REQUIREMENTS:
        value = evidence.get(field)
        if field == "regression_cases":
            if int(value or 0) < 2:
                missing.append("regression_cases>=2")
        elif not value:
            missing.append(field)
    return {
        "approved": not missing,
        "status": "approved" if not missing else "not_ready",
        "missing_requirements": missing,
        "target": _clean(evidence.get("promotion_target")) or "ckb_review_queue",
    }


def release_decision(release_report: dict, clusters=None, queue=None) -> dict:
    unresolved_safety = [
        item for item in clusters or []
        if item.get("route") in {"component_identity", "meal_coherence"}
        and item.get("status") == "batch_review"
    ]
    blockers = []
    if not release_report.get("production_ready"):
        blockers.append("release_gates_failed")
    if unresolved_safety:
        blockers.append("unresolved_high_risk_learning_clusters")
    return {
        "release": not blockers,
        "status": "release" if not blockers else "hold",
        "blockers": blockers,
        "unresolved_high_risk_clusters": len(unresolved_safety),
        "queued_learning_items": len(queue or []),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "policy_version": "sns_release_learning_v1",
    }


def monitoring_snapshot(reports, clusters, queue, promotion_results=None) -> dict:
    return {
        "reports": len(reports or []),
        "negative_reports": sum(
            str(item.get("report_outcome") or item.get("p_report_outcome") or "NG").upper() == "NG"
            for item in reports or []
        ),
        "clusters": len(clusters or []),
        "batch_review_clusters": sum(item.get("status") == "batch_review" for item in clusters or []),
        "enrichment_queue": len(queue or []),
        "promotions_approved": sum(item.get("approved") for item in promotion_results or []),
    }

