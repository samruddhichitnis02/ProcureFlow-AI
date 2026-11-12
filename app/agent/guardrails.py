from typing import Dict, Any, Tuple
from app.config import settings

SENSITIVE_ACTION_TYPES = {
    "REFUND_CUSTOMER",
    "REFUND_PAYMENT_DISCREPANCY",
    "PENALIZE_SELLER",
    "SUSPEND_SELLER",
    "CONTRACT_TERMINATION",
}


def assess_action_risk(
    action: Dict[str, Any], refund_threshold: float = settings.HIGH_RISK_REFUND_THRESHOLD
) -> Tuple[str, bool, str]:
    """
    Evaluates policy guardrails for an AI agent's proposed procurement action.
    Returns:
        risk_level: "LOW", "MEDIUM", "HIGH"
        requires_approval: bool
        reason: str
    """
    action_type = (action.get("action_type") or "").upper()
    amount = float(action.get("amount", 0.0))

    # Condition 1: Direct high-risk sensitive action types
    if "SUSPEND" in action_type or "TERMINAT" in action_type:
        return "HIGH", True, f"Action '{action_type}' impacts enterprise supplier contract terms."

    # Condition 2: Financial threshold checks
    if amount >= refund_threshold:
        return (
            "HIGH",
            True,
            f"Financial impact (${amount:.2f}) exceeds autonomous approval threshold (${refund_threshold:.2f}).",
        )

    if "REFUND" in action_type or "PENAL" in action_type:
        if amount > 50.0:
            return (
                "MEDIUM",
                True,
                f"Financial adjustment of ${amount:.2f} requires procurement lead review.",
            )
        return (
            "LOW",
            False,
            f"Standard low-value courtesy credit of ${amount:.2f} approved autonomously.",
        )

    # Condition 3: Informational and standard operations
    return "LOW", False, "Action complies with standard operational autonomy policies."

