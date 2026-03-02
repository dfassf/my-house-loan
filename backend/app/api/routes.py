import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from app.calculator.optimizer import simulate
from app.rules.product_loader import clear_cache, load_bogeumjari, load_didimdol
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


# ── 관리자 엔드포인트 ───────────────────────────────────────


@router.post("/admin/refresh-all")
async def refresh_all():
    """관리자용: 금리 + 자격요건 전체 수동 갱신."""
    from app.db import engine, SessionLocal
    from app.fetchers.scheduler import run_all_fetchers

    if engine is None:
        raise HTTPException(status_code=503, detail="DB 미설정. 갱신 불가.")

    try:
        with SessionLocal() as session:
            results = await run_all_fetchers(session)

        clear_cache()
        return {"status": "ok", "results": results}
    except Exception as e:
        logger.error(f"갱신 오류: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="갱신 중 문제가 생겼어요.") from e


@router.put("/admin/product/{product_id}")
async def update_product(product_id: str, updates: dict[str, Any]):
    """관리자용: 상품 데이터 수동 수정.

    자격요건, 금리, 우대조건 등 개별 필드를 부분 수정 가능.
    예: {"max_housing_price": 900000000, "max_income": 80000000}
    """
    from datetime import datetime, timezone

    from sqlalchemy import select

    from app.db import engine, SessionLocal
    from app.fetchers.models import PolicyProductCache

    if engine is None:
        raise HTTPException(status_code=503, detail="DB 미설정.")

    if product_id not in ("didimdol", "bogeumjari"):
        raise HTTPException(status_code=400, detail=f"알 수 없는 상품: {product_id}")

    now = datetime.now(timezone.utc)

    try:
        with SessionLocal() as session:
            existing = session.execute(
                select(PolicyProductCache)
                .where(PolicyProductCache.product_id == product_id)
            ).scalar_one_or_none()

            if existing:
                data = existing.product_data.copy()
                changed_fields = []
                for key, value in updates.items():
                    if key.startswith("_"):
                        continue
                    old = data.get(key)
                    if old != value:
                        changed_fields.append(f"{key}: {old} → {value}")
                    data[key] = value

                existing.product_data = data
                existing.source = "manual_admin"
                existing.updated_at = now

                # 어떤 섹션이 변경됐는지 추적
                rate_keys = {"income_rate_tiers", "newlywed_rate_tiers", "min_rate_floor", "min_rate_floor_newlywed"}
                elig_keys = {"max_housing_price", "max_income", "max_net_assets", "max_loan_amount",
                             "max_housing_price_newlywed", "max_income_married", "max_income_newlywed",
                             "max_loan_amount_newlywed", "max_loan_amount_first_time",
                             "max_ltv_pct", "max_ltv_pct_first_time", "max_area_m2", "max_area_m2_urban",
                             "requires_homeless"}
                discount_keys = {"discount_conditions", "max_total_discount"}

                if set(updates.keys()) & rate_keys:
                    existing.rate_updated_at = now
                if set(updates.keys()) & elig_keys:
                    existing.eligibility_updated_at = now
                if set(updates.keys()) & discount_keys:
                    existing.discount_updated_at = now

                logger.info("[admin] %s 수동 수정: %s", product_id, changed_fields)
            else:
                # DB에 없으면 새로 생성 (JSON 기본값 + 수정사항)
                from app.rules.product_loader import _load_json

                json_file = f"{product_id}.json"
                base_data = _load_json(json_file)
                for key, value in updates.items():
                    if not key.startswith("_"):
                        base_data[key] = value

                session.add(PolicyProductCache(
                    product_id=product_id,
                    product_data=base_data,
                    source="manual_admin",
                    eligibility_updated_at=now,
                    rate_updated_at=now,
                ))

            session.commit()

        clear_cache()
        return {"status": "ok", "product_id": product_id, "updated_fields": list(updates.keys())}

    except Exception as e:
        logger.error(f"상품 수정 오류: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="상품 수정 중 문제가 생겼어요.") from e


@router.get("/admin/product/{product_id}")
async def get_product_data(product_id: str):
    """관리자용: 현재 적용 중인 상품 데이터 전체 조회."""
    if product_id == "didimdol":
        data = load_didimdol()
    elif product_id == "bogeumjari":
        data = load_bogeumjari()
    else:
        raise HTTPException(status_code=400, detail=f"알 수 없는 상품: {product_id}")

    return {"product_id": product_id, "data": dict(data)}


@router.get("/admin/status")
async def admin_status():
    """관리자용: 전체 시스템 상태 (캐시 + 알림 + 수집 이력)."""
    from app.db import engine, SessionLocal

    if engine is None:
        return {
            "db_connected": False,
            "message": "DB 미설정. JSON 폴백 사용 중.",
            "data_source": "json_fallback",
        }

    try:
        from sqlalchemy import select

        from app.fetchers.models import (
            BankAvgRateCache,
            HfNewsWatch,
            PolicyProductCache,
            RateFetchLog,
        )

        with SessionLocal() as session:
            # 정책대출 캐시 현황
            policy_stmt = (
                select(
                    PolicyProductCache.product_id,
                    PolicyProductCache.source,
                    PolicyProductCache.rate_updated_at,
                    PolicyProductCache.eligibility_updated_at,
                    PolicyProductCache.discount_updated_at,
                    PolicyProductCache.updated_at,
                )
            )
            policy_rows = session.execute(policy_stmt).all()

            # ECOS 최신
            ecos_stmt = (
                select(BankAvgRateCache.stat_month, BankAvgRateCache.rate_value, BankAvgRateCache.fetched_at)
                .order_by(BankAvgRateCache.stat_month.desc())
                .limit(1)
            )
            ecos_row = session.execute(ecos_stmt).first()

            # 미확인 보도자료 알림
            alert_stmt = (
                select(HfNewsWatch.article_id, HfNewsWatch.title, HfNewsWatch.keywords_matched, HfNewsWatch.detected_at)
                .where(HfNewsWatch.is_relevant == True, HfNewsWatch.acknowledged == False)
                .order_by(HfNewsWatch.detected_at.desc())
                .limit(10)
            )
            alert_rows = session.execute(alert_stmt).all()

            # 최근 수집 로그
            log_stmt = (
                select(RateFetchLog.source, RateFetchLog.status, RateFetchLog.message, RateFetchLog.fetched_at)
                .order_by(RateFetchLog.fetched_at.desc())
                .limit(15)
            )
            log_rows = session.execute(log_stmt).all()

        return {
            "db_connected": True,
            "data_source": "db_cache",
            "products": [
                {
                    "product_id": r.product_id,
                    "source": r.source,
                    "rate_updated_at": r.rate_updated_at.isoformat() if r.rate_updated_at else None,
                    "eligibility_updated_at": r.eligibility_updated_at.isoformat() if r.eligibility_updated_at else None,
                    "discount_updated_at": r.discount_updated_at.isoformat() if r.discount_updated_at else None,
                    "last_updated": r.updated_at.isoformat() if r.updated_at else None,
                }
                for r in policy_rows
            ],
            "ecos_latest": {
                "stat_month": ecos_row.stat_month,
                "rate_value": float(ecos_row.rate_value),
                "fetched_at": ecos_row.fetched_at.isoformat() if ecos_row.fetched_at else None,
            } if ecos_row else None,
            "unacknowledged_alerts": [
                {
                    "article_id": r.article_id,
                    "title": r.title,
                    "keywords": r.keywords_matched,
                    "detected_at": r.detected_at.isoformat() if r.detected_at else None,
                }
                for r in alert_rows
            ],
            "alert_count": len(alert_rows),
            "recent_logs": [
                {
                    "source": r.source,
                    "status": r.status,
                    "message": r.message,
                    "fetched_at": r.fetched_at.isoformat() if r.fetched_at else None,
                }
                for r in log_rows
            ],
        }
    except Exception as e:
        return {"db_connected": True, "error": str(e)}


@router.post("/admin/alerts/{article_id}/acknowledge")
async def acknowledge_alert(article_id: str):
    """관리자용: 보도자료 알림 확인 처리."""
    from sqlalchemy import select, update

    from app.db import engine, SessionLocal
    from app.fetchers.models import HfNewsWatch

    if engine is None:
        raise HTTPException(status_code=503, detail="DB 미설정.")

    try:
        with SessionLocal() as session:
            stmt = (
                update(HfNewsWatch)
                .where(HfNewsWatch.article_id == article_id)
                .values(acknowledged=True)
            )
            result = session.execute(stmt)
            session.commit()

            if result.rowcount == 0:
                raise HTTPException(status_code=404, detail="해당 기사를 찾을 수 없어요.")

        return {"status": "ok", "article_id": article_id, "acknowledged": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
