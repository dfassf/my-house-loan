import logging

from fastapi import APIRouter, HTTPException

from app.calculator.optimizer import simulate
from app.rules.product_loader import load_bogeumjari, load_didimdol
from app.schemas.loan_input import LoanSimulationRequest
from app.llm.explainer import explain_result
from app.schemas.loan_result import SimulationResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/products")
async def list_products():
    """사용 가능한 대출 상품 목록."""
    didimdol = load_didimdol()
    bogeumjari = load_bogeumjari()

    return {
        "products": [
            {
                "id": didimdol["product_id"],
                "name": didimdol["product_name"],
                "type": didimdol["product_type"],
            },
            {
                "id": bogeumjari["product_id"],
                "name": bogeumjari["product_name"],
                "type": bogeumjari["product_type"],
            },
        ]
    }


@router.post("/simulate", response_model=SimulationResponse)
async def run_simulation(request: LoanSimulationRequest):
    """대출 시뮬레이션 실행."""
    try:
        result = simulate(request)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"시뮬레이션 오류: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="시뮬레이션 처리 중 문제가 생겼어요.") from e


@router.post("/explain")
async def explain(result: SimulationResponse):
    """시뮬레이션 결과에 대한 AI 설명 생성."""
    try:
        explanation = await explain_result(result)
        return {"explanation": explanation}
    except Exception as e:
        logger.error(f"설명 생성 오류: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="설명을 만드는 중 문제가 생겼어요.") from e
