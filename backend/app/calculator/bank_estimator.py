"""은행 주택담보대출 금리 추정 모듈."""

from app.rules.product_loader import load_bank_average
from app.schemas.loan_input import LoanSimulationRequest


def estimate_bank_rate(request: LoanSimulationRequest) -> float:
    """사용자 신용점수 기반 은행 추정 금리 (%)."""
    data = load_bank_average()

    base_rates = data.get("base_rates", {})
    default_key = data.get("default_rate_key", "variable")
    base_val = base_rates.get(default_key, 3.70)
    base_rate = float(base_val) if isinstance(base_val, (int, float)) else 3.70

    adjustment = _credit_adjustment(request.credit_score, data)

    return round(base_rate + adjustment, 2)


def _credit_adjustment(credit_score: int, data: dict) -> float:
    """신용점수별 금리 보정."""
    adjustments = data.get("credit_adjustments", [])

    for adj in adjustments:
        if adj["min_score"] <= credit_score <= adj["max_score"]:
            return adj["adjustment_pct"]

    return 0.0
