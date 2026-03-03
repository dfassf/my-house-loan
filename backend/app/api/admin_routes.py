import logging
from datetime import datetime, timezone
from hmac import compare_digest
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException

from app.cache import PolicyProductEntry, cache
from app.config import settings
from app.rules.product_loader import clear_cache, load_base_product_data, load_bogeumjari, load_didimdol

logger = logging.getLogger(__name__)

admin_router = APIRouter()


def verify_admin_key(x_admin_key: str | None = Header(default=None, alias="X-Admin-Key")) -> None:
    """관리자 API 헤더 키 검증."""
    expected_key = settings.admin_api_key.strip()
    if not expected_key:
        raise HTTPException(status_code=503, detail="관리자 인증키가 설정되지 않았어요.")

    if x_admin_key is None or not compare_digest(x_admin_key, expected_key):
        raise HTTPException(status_code=401, detail="관리자 인증에 실패했어요.")


@admin_router.post("/refresh-all")
async def refresh_all(_auth: None = Depends(verify_admin_key)):
    """관리자용: 금리 + 자격요건 전체 수동 갱신."""
    from app.fetchers.scheduler import run_all_fetchers

    try:
        results = await run_all_fetchers()
        clear_cache()
        return {"status": "ok", "results": results}
    except Exception as e:
        logger.error(f"갱신 오류: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="갱신 중 문제가 생겼어요.") from e


@admin_router.put("/product/{product_id}")
async def update_product(
    product_id: str,
    updates: dict[str, Any],
    _auth: None = Depends(verify_admin_key),
):
    """관리자용: 상품 데이터 수동 수정.

    자격요건, 금리, 우대조건 등 개별 필드를 부분 수정 가능.
    예: {"max_housing_price": 900000000, "max_income": 80000000}
    """
    if product_id not in ("didimdol", "bogeumjari"):
        raise HTTPException(status_code=400, detail=f"알 수 없는 상품: {product_id}")

    now = datetime.now(timezone.utc)

    try:
        existing = cache.policy_products.get(product_id)

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
            base_data = load_base_product_data(product_id)
            for key, value in updates.items():
                if not key.startswith("_"):
                    base_data[key] = value

            cache.policy_products[product_id] = PolicyProductEntry(
                product_id=product_id,
                product_data=base_data,
                source="manual_admin",
                eligibility_updated_at=now,
                rate_updated_at=now,
            )

        clear_cache()
        return {"status": "ok", "product_id": product_id, "updated_fields": list(updates.keys())}

    except Exception as e:
        logger.error(f"상품 수정 오류: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="상품 수정 중 문제가 생겼어요.") from e


@admin_router.get("/product/{product_id}")
async def get_product_data(
    product_id: str,
    _auth: None = Depends(verify_admin_key),
):
    """관리자용: 현재 적용 중인 상품 데이터 전체 조회."""
    if product_id == "didimdol":
        data = load_didimdol()
    elif product_id == "bogeumjari":
        data = load_bogeumjari()
    else:
        raise HTTPException(status_code=400, detail=f"알 수 없는 상품: {product_id}")

    return {"product_id": product_id, "data": dict(data)}


@admin_router.get("/status")
async def admin_status(_auth: None = Depends(verify_admin_key)):
    """관리자용: 전체 시스템 상태 (캐시 + 알림 + 수집 이력)."""
    unacknowledged = [
        entry for entry in cache.hf_news.values()
        if entry.is_relevant and not entry.acknowledged
    ]

    return {
        "data_source": "in_memory_cache",
        "products": [
            {
                "product_id": entry.product_id,
                "source": entry.source,
                "rate_updated_at": entry.rate_updated_at.isoformat() if entry.rate_updated_at else None,
                "eligibility_updated_at": entry.eligibility_updated_at.isoformat() if entry.eligibility_updated_at else None,
                "discount_updated_at": entry.discount_updated_at.isoformat() if entry.discount_updated_at else None,
                "last_updated": entry.updated_at.isoformat() if entry.updated_at else None,
            }
            for entry in cache.policy_products.values()
        ],
        "ecos_latest": cache.get_latest_avg_entry(),
        "unacknowledged_alerts": [
            {
                "article_id": entry.article_id,
                "title": entry.title,
                "keywords": entry.keywords_matched,
                "detected_at": entry.detected_at.isoformat(),
            }
            for entry in sorted(unacknowledged, key=lambda e: e.detected_at, reverse=True)[:10]
        ],
        "alert_count": len(unacknowledged),
        "recent_logs": [
            {
                "source": log.source,
                "status": log.status,
                "message": log.message,
                "fetched_at": log.fetched_at.isoformat(),
            }
            for log in list(cache.fetch_logs)[:15]
        ],
    }


@admin_router.post("/alerts/{article_id}/acknowledge")
async def acknowledge_alert(
    article_id: str,
    _auth: None = Depends(verify_admin_key),
):
    """관리자용: 보도자료 알림 확인 처리."""
    entry = cache.hf_news.get(article_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="해당 기사를 찾을 수 없어요.")

    entry.acknowledged = True
    return {"status": "ok", "article_id": article_id, "acknowledged": True}
