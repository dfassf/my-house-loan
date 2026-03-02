"""시뮬레이션 결과 설명 생성 — Gemini로 자연어 설명."""

import logging

from google.genai import types

from app.config import settings
from app.llm.client import MODEL, call_with_limits, get_client, retry
from app.schemas.loan_result import SimulationResponse

logger = logging.getLogger(__name__)

EXPLAIN_SYSTEM_PROMPT = """당신은 한국의 주택담보대출 전문 상담사예요.
사용자에게 대출 계산 결과를 쉽고 친근하게 설명해 주세요.

규칙:
- 해요체 사용 (합니다/입니다 대신 해요/이에요)
- "추천"이라는 단어 사용 금지. "계산 결과"로 대체
- 특정 은행명 언급 금지
- 각 조합의 장단점을 비교
- 핵심 수치(금리, 월납입, 총이자)를 강조
- 200자 이내로 간결하게
- 마지막에 반드시 "실제 조건은 금융기관 심사에 따라 달라질 수 있어요" 문구 포함
"""


def _build_explain_prompt(result: SimulationResponse) -> str:
    lines: list[str] = ["대출 시뮬레이션 결과를 설명해주세요.\n"]

    for combo in result.combinations[:5]:
        lines.append(f"[{combo.rank}순위] {combo.label}")
        lines.append(f"  총 대출: {combo.total_loan_amount // 10000:,}만원")
        lines.append(f"  가중평균금리: {combo.weighted_avg_rate}%")
        lines.append(f"  월 납입: {combo.total_monthly_payment // 10000:,}만원")
        lines.append(f"  총 이자: {combo.total_interest // 10000:,}만원")
        lines.append(f"  DSR: {combo.dsr_ratio}%, LTV: {combo.ltv_ratio}%")

        for product in combo.products:
            badge = "정책" if product.product_type == "policy" else "은행"
            lines.append(f"  [{badge}] {product.product_name} {product.annual_rate_pct}% {product.loan_amount // 10000:,}만원")
            if product.discount_details:
                lines.append(f"    우대: {', '.join(product.discount_details)}")
        lines.append("")

    if result.warnings:
        lines.append("경고: " + " / ".join(result.warnings))

    return "\n".join(lines)


async def explain_result(result: SimulationResponse) -> str:
    """시뮬레이션 결과에 대한 자연어 설명 생성."""
    api_key = settings.gemini_api_key
    if not api_key:
        return "AI 설명을 만들려면 Gemini API 키가 필요해요."

    prompt = _build_explain_prompt(result)

    async def _call() -> str:
        response = await get_client(api_key).aio.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=EXPLAIN_SYSTEM_PROMPT,
                temperature=0.3,
                max_output_tokens=512,
            ),
        )
        text = response.text
        if not text:
            raise ValueError("LLM 빈 응답")
        return text

    return await retry(lambda: call_with_limits(_call, "explain"), "explain")
