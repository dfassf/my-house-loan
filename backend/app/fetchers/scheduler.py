"""금리 + 자격요건 데이터 수집 스케줄러.

FastAPI lifespan에서 백그라운드로 동작.
각 소스별 TTL 기반 갱신 + 인메모리 캐싱 + 변경 감지 알림.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from app.cache import HfNewsEntry, PolicyProductEntry, cache
from app.fetchers.data_go_kr import BogeumjariFetcher, DidimdolFetcher
from app.fetchers.ecos import EcosFetcher
from app.fetchers.finlife import FinlifeFetcher
from app.fetchers.hf_scraper import (
    HfBogeumjariScraper,
    HfDidimdolScraper,
    HfNewsScraper,
)
from app.rules.product_loader import clear_cache as clear_product_cache

logger = logging.getLogger(__name__)

KST = timezone(timedelta(hours=9))

# TTL 설정 (시간 단위)
_TTL_BOGEUMJARI_HOURS = 24
_TTL_DIDIMDOL_HOURS = 12
_TTL_FINLIFE_HOURS = 24
_TTL_ECOS_HOURS = 48
_TTL_NEWS_HOURS = 6

# 체크 간격
_CHECK_INTERVAL_SECONDS = 3600  # 1시간


def _is_cache_expired(last_fetched: datetime | None, ttl_hours: int) -> bool:
    if last_fetched is None:
        return True
    now = datetime.now(timezone.utc)
    return (now - last_fetched) > timedelta(hours=ttl_hours)


# ── 정책대출 수집 (금리 + 자격요건) ─────────────────────────


async def _fetch_and_cache_policy(
    fetcher_api: DidimdolFetcher | BogeumjariFetcher,
    fetcher_hf: HfDidimdolScraper | HfBogeumjariScraper,
    product_id: str,
) -> None:
    """정책대출 데이터 수집 → 인메모리 캐싱.

    1순위 금리: data.go.kr API
    2순위 금리 + 자격요건: HF 홈페이지 크롤링
    """
    now = datetime.now(timezone.utc)

    existing = cache.policy_products.get(product_id)
    product_data: dict[str, Any] = existing.product_data.copy() if existing else {}
    source_parts: list[str] = []
    rate_updated = False
    eligibility_updated = False

    # ── 금리 수집 ──

    # 1순위: data.go.kr
    api_result = await fetcher_api.fetch()
    if api_result.success and api_result.data.get("income_rate_tiers"):
        product_data["income_rate_tiers"] = api_result.data["income_rate_tiers"]
        source_parts.append(fetcher_api.source_name)
        rate_updated = True
    else:
        logger.info("[%s] data.go.kr 금리 수집 실패, HF 크롤링으로 대체", product_id)

    # 2순위: HF 크롤링 (금리 + 자격요건)
    hf_result = await fetcher_hf.fetch()
    if hf_result.success:
        hf_data = hf_result.data

        # 금리 (API 실패 시에만 HF 금리 사용)
        rate_info = hf_data.get("rate_info")
        if not rate_updated and rate_info:
            product_data["_hf_rate_info"] = rate_info
            source_parts.append(fetcher_hf.source_name + ":rate")
            rate_updated = True

        # 자격요건 (항상 HF에서 갱신 시도)
        elig_info = hf_data.get("eligibility_info")
        if elig_info:
            _merge_eligibility(product_data, elig_info)
            source_parts.append(fetcher_hf.source_name + ":eligibility")
            eligibility_updated = True

    if not source_parts:
        cache.log_fetch(f"policy_{product_id}", "fail", "금리+자격요건 모두 수집 실패")
        return

    source_str = "+".join(source_parts)
    if existing:
        existing.product_data = product_data
        existing.source = source_str
        existing.updated_at = now
        if rate_updated:
            existing.rate_updated_at = now
        if eligibility_updated:
            existing.eligibility_updated_at = now
    else:
        cache.policy_products[product_id] = PolicyProductEntry(
            product_id=product_id,
            product_data=product_data,
            source=source_str,
            rate_updated_at=now if rate_updated else None,
            eligibility_updated_at=now if eligibility_updated else None,
        )

    cache.log_fetch(f"policy_{product_id}", "success", source_str)
    clear_product_cache()
    logger.info("[%s] 상품 캐시 갱신 완료 (source=%s)", product_id, source_str)


def _merge_eligibility(product_data: dict, elig_info: dict) -> None:
    """크롤링된 자격요건을 기존 상품 데이터에 병합.

    크롤링 값이 있을 때만 덮어씀 (부분 갱신).
    """
    field_map = {
        "max_housing_price": "max_housing_price",
        "max_housing_price_newlywed": "max_housing_price_newlywed",
        "max_loan_amount": "max_loan_amount",
        "max_income": "max_income",
        "max_income_newlywed": "max_income_newlywed",
        "max_net_assets": "max_net_assets",
        "max_area_m2": "max_area_m2",
        "max_area_m2_urban": "max_area_m2_urban",
        "requires_homeless": "requires_homeless",
    }

    for elig_key, product_key in field_map.items():
        if elig_key in elig_info and elig_info[elig_key] is not None:
            old_val = product_data.get(product_key)
            new_val = elig_info[elig_key]
            if old_val != new_val:
                logger.info(
                    "[eligibility] %s 변경 감지: %s → %s",
                    product_key, old_val, new_val,
                )
            product_data[product_key] = new_val


# ── 은행 금리 수집 ──────────────────────────────────────────


async def _fetch_and_cache_bank_rates() -> None:
    fetcher = FinlifeFetcher()
    result = await fetcher.fetch()

    if not result.success:
        cache.log_fetch(fetcher.source_name, "fail", result.error)
        return

    products = result.data.get("products", [])
    dcls_month = result.data.get("dcls_month", "")

    new_rates: list[dict[str, Any]] = []
    for prod in products:
        new_rates.append({
            "dcls_month": dcls_month,
            "fin_co_nm": prod.get("fin_co_nm", ""),
            "fin_prdt_nm": prod.get("fin_prdt_nm", ""),
            "mrtg_type": prod.get("mrtg_type", ""),
            "rpay_type": prod.get("rpay_type", ""),
            "lend_rate_type": prod.get("lend_rate_type", ""),
            "rate_min": prod.get("rate_min"),
            "rate_max": prod.get("rate_max"),
            "rate_avg": prod.get("rate_avg"),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        })

    cache.bank_rates = new_rates
    cache.log_fetch(fetcher.source_name, "success", f"{len(products)} products, month={dcls_month}")
    logger.info("[finlife] 은행 금리 캐시 갱신 완료 (%d 상품)", len(products))


async def _fetch_and_cache_ecos() -> None:
    fetcher = EcosFetcher()
    result = await fetcher.fetch()

    if not result.success:
        cache.log_fetch(fetcher.source_name, "fail", result.error)
        return

    for entry in result.data.get("monthly_rates", []):
        cache.bank_avg_rates[entry["stat_month"]] = float(entry["rate_value"])

    cache.log_fetch(fetcher.source_name, "success")
    clear_product_cache()
    logger.info("[ecos] 평균금리 캐시 갱신 완료")


# ── HF 보도자료 모니터링 ────────────────────────────────────


async def _monitor_hf_news() -> list[dict]:
    """HF 보도자료 크롤링 → 새 기사 중 관련 기사 감지."""
    fetcher = HfNewsScraper()
    result = await fetcher.fetch()

    if not result.success:
        cache.log_fetch(fetcher.source_name, "fail", result.error)
        return []

    articles = result.data.get("articles", [])
    new_alerts: list[dict] = []

    for article in articles:
        article_id = article["article_id"]

        if article_id in cache.hf_news:
            continue

        cache.hf_news[article_id] = HfNewsEntry(
            article_id=article_id,
            title=article["title"],
            is_relevant=article["is_relevant"],
            keywords_matched=",".join(article.get("keywords_matched", [])),
        )

        if article["is_relevant"]:
            new_alerts.append(article)
            logger.warning(
                "[HF 보도자료 알림] 정책 변경 가능성: '%s' (키워드: %s)",
                article["title"],
                article.get("keywords_matched"),
            )

    if new_alerts:
        cache.log_fetch(
            "hf_news", "alert",
            f"{len(new_alerts)}건 관련 기사 감지: {[a['title'] for a in new_alerts]}"
        )
    else:
        cache.log_fetch("hf_news", "success", f"{len(articles)}건 확인, 새 알림 없음")

    return new_alerts


# ── 통합 실행 ───────────────────────────────────────────────


async def run_all_fetchers() -> dict[str, Any]:
    """모든 소스에서 수집 실행. 수동 갱신 엔드포인트용."""
    results: dict[str, Any] = {}

    try:
        await _fetch_and_cache_policy(
            DidimdolFetcher(), HfDidimdolScraper(), "didimdol",
        )
        results["didimdol"] = "success"
    except Exception as e:
        results["didimdol"] = f"error: {e}"
        logger.exception("[didimdol] 수집 실패")

    try:
        await _fetch_and_cache_policy(
            BogeumjariFetcher(), HfBogeumjariScraper(), "bogeumjari",
        )
        results["bogeumjari"] = "success"
    except Exception as e:
        results["bogeumjari"] = f"error: {e}"
        logger.exception("[bogeumjari] 수집 실패")

    try:
        await _fetch_and_cache_bank_rates()
        results["finlife"] = "success"
    except Exception as e:
        results["finlife"] = f"error: {e}"
        logger.exception("[finlife] 수집 실패")

    try:
        await _fetch_and_cache_ecos()
        results["ecos"] = "success"
    except Exception as e:
        results["ecos"] = f"error: {e}"
        logger.exception("[ecos] 수집 실패")

    try:
        alerts = await _monitor_hf_news()
        results["hf_news"] = {
            "status": "alert" if alerts else "success",
            "new_alerts": len(alerts),
            "alert_titles": [a["title"] for a in alerts],
        }
    except Exception as e:
        results["hf_news"] = f"error: {e}"
        logger.exception("[hf_news] 모니터링 실패")

    return results


async def rate_update_loop() -> None:
    """백그라운드 금리+자격요건 갱신 루프."""
    logger.info("[scheduler] 초기 데이터 수집 시작")
    try:
        await run_all_fetchers()
    except Exception:
        logger.exception("[scheduler] 초기 수집 실패")

    while True:
        await asyncio.sleep(_CHECK_INTERVAL_SECONDS)

        try:
            # 보금자리론: 24시간마다
            last = cache.get_last_fetch_time("policy_bogeumjari")
            if _is_cache_expired(last, _TTL_BOGEUMJARI_HOURS):
                await _fetch_and_cache_policy(
                    BogeumjariFetcher(), HfBogeumjariScraper(), "bogeumjari",
                )

            # 디딤돌: 12시간마다
            last = cache.get_last_fetch_time("policy_didimdol")
            if _is_cache_expired(last, _TTL_DIDIMDOL_HOURS):
                await _fetch_and_cache_policy(
                    DidimdolFetcher(), HfDidimdolScraper(), "didimdol",
                )

            # finlife 은행금리: 24시간마다
            last = cache.get_last_fetch_time("finlife")
            if _is_cache_expired(last, _TTL_FINLIFE_HOURS):
                await _fetch_and_cache_bank_rates()

            # ECOS 평균금리: 48시간마다
            last = cache.get_last_fetch_time("ecos")
            if _is_cache_expired(last, _TTL_ECOS_HOURS):
                await _fetch_and_cache_ecos()

            # HF 보도자료: 6시간마다
            last = cache.get_last_fetch_time("hf_news")
            if _is_cache_expired(last, _TTL_NEWS_HOURS):
                await _monitor_hf_news()

        except Exception:
            logger.exception("[scheduler] 갱신 루프 에러")
