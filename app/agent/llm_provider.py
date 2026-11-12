import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from app.config import settings

logger = logging.getLogger(__name__)


class BaseLLMClient(ABC):
    @abstractmethod
    def reason(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Execute reasoning prompt and return response."""
        pass


class MockReasoningEngine(BaseLLMClient):
    """
    Zero-Cost Local Deterministic Reasoning Engine.
    Simulates Claude 3.5 Sonnet agent reasoning with zero external network calls,
    zero latency cost, and zero monetary cost.
    Generates realistic root cause analysis, evidence synthesis, and structured procurement actions.
    """

    def reason(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        # Check if structured JSON diagnosis or action recommendation is requested
        if "GENERATE_DIAGNOSIS_JSON" in prompt:
            return json.dumps({
                "root_cause": "Carrier transit bottleneck compounded by dispatch lag",
                "delay_attribution": "CARRIER_LOGISTICS_DELAY",
                "carrier_responsibility_pct": 75.0,
                "seller_responsibility_pct": 25.0,
                "summary": "Order dispatched within SLA window but detained at regional transit distribution center beyond estimated delivery date.",
                "evidence_citations": ["orders.order_estimated_delivery_date", "orders.order_delivered_carrier_date", "order_reviews.comment"],
            })

        if "GENERATE_ACTION_JSON" in prompt:
            # Check context inside prompt
            if "has_payment_issue: true" in prompt.lower() or "discrepancy" in prompt.lower():
                return json.dumps({
                    "action_type": "REFUND_PAYMENT_DISCREPANCY",
                    "amount": 145.50,
                    "target_entity": "CUSTOMER",
                    "reason": "Payment transaction mismatch detected between billed line items and captured receipt.",
                    "mitigation": "Issue automated refund ledger adjustment and notify payment gateway.",
                    "requires_human_approval": True,
                    "risk_level": "HIGH",
                })
            elif "delay_days" in prompt and "late" in prompt.lower():
                return json.dumps({
                    "action_type": "EXPEDITE_AND_ISSUE_CREDIT",
                    "amount": 35.00,
                    "target_entity": "CUSTOMER_AND_CARRIER",
                    "reason": "Shipment exceeded SLA window by over 5 business days without carrier milestone update.",
                    "mitigation": "File high-priority logistics trace, issue $35 convenience voucher to customer.",
                    "requires_human_approval": False,
                    "risk_level": "LOW",
                })
            else:
                return json.dumps({
                    "action_type": "AUDIT_SELLER_SLA",
                    "amount": 0.0,
                    "target_entity": "SELLER",
                    "reason": "Routine procurement health inspection confirmed fulfillment parameters within acceptable limits.",
                    "mitigation": "Log compliance check in procurement registry.",
                    "requires_human_approval": False,
                    "risk_level": "LOW",
                })

        return (
            "ProcureFlow AI has verified order records across database tables and semantic vector logs. "
            "All telemetry has been cross-referenced with enterprise procurement policies."
        )


class ClaudeLLMClient(BaseLLMClient):
    """
    Anthropic Claude 3.5 Sonnet Integration.
    Activated seamlessly when ANTHROPIC_API_KEY is configured.
    """

    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        import anthropic

        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def reason(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        messages = [{"role": "user", "content": prompt}]
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "max_tokens": 1500,
            "messages": messages,
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        response = self.client.messages.create(**kwargs)
        return response.content[0].text


def get_llm_client() -> BaseLLMClient:
    """
    Returns configured LLM client:
    - If ANTHROPIC_API_KEY is present and LLM_PROVIDER is 'claude', returns ClaudeLLMClient.
    - Otherwise defaults to MockReasoningEngine (100% Free, Offline, Deterministic).
    """
    if settings.LLM_PROVIDER.lower() == "claude" and settings.ANTHROPIC_API_KEY:
        try:
            return ClaudeLLMClient(
                api_key=settings.ANTHROPIC_API_KEY, model=settings.CLAUDE_MODEL
            )
        except Exception as e:
            logger.warning("Failed to initialize Claude client (%s). Falling back to MockReasoningEngine.", e)

    return MockReasoningEngine()

