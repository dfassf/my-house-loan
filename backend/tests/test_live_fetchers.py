"""실데이터 Fetcher 테스트 (실제 외부 API 호출).

실행: python -m pytest tests/test_live_fetchers.py -v -s
"""

import json

import pytest

pytestmark = pytest.mark.asyncio


def _pp(label: str, data):
    """결과 예쁘게 출력."""
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    if isinstance(data, dict):
        print(json.dumps(data, ensure_ascii=False, indent=2, default=str))
    else:
        print(data)
    print()


async def test_hf_didimdol():
    """HF 디딤돌 금리+자격요건 크롤링 (키 불필요)."""
    from app.fetchers.hf_scraper import HfDidimdolScraper

    scraper = HfDidimdolScraper()
    result = await scraper.fetch()

    _pp("HF 디딤돌 크롤링", {
        "success": result.success,
        "error": result.error,
        "data": result.data,
    })

    assert result.success, f"HF 디딤돌 크롤링 실패: {result.error}"
    assert result.data.get("rate_info") or result.data.get("eligibility_info"), \
        "금리 또는 자격요건 중 하나는 파싱되어야 함"


async def test_hf_bogeumjari():
    """HF 보금자리론 금리+자격요건 크롤링 (키 불필요)."""
    from app.fetchers.hf_scraper import HfBogeumjariScraper

    scraper = HfBogeumjariScraper()
    result = await scraper.fetch()

    _pp("HF 보금자리론 크롤링", {
        "success": result.success,
        "error": result.error,
        "data": result.data,
    })

    assert result.success, f"HF 보금자리론 크롤링 실패: {result.error}"


async def test_hf_news():
    """HF 보도자료 크롤링 (키 불필요)."""
    from app.fetchers.hf_scraper import HfNewsScraper

    scraper = HfNewsScraper()
    result = await scraper.fetch()

    _pp("HF 보도자료", {
        "success": result.success,
        "error": result.error,
        "article_count": len(result.data.get("articles", [])) if result.data else 0,
        "articles": result.data.get("articles", [])[:5] if result.data else [],
    })

    assert result.success, f"HF 보도자료 크롤링 실패: {result.error}"


async def test_data_go_kr_didimdol():
    """data.go.kr 디딤돌 금리 API."""
    from app.config import settings
    if not settings.data_go_kr_service_key:
        pytest.skip("DATA_GO_KR_SERVICE_KEY 미설정")

    from app.fetchers.data_go_kr import DidimdolFetcher

    fetcher = DidimdolFetcher()
    result = await fetcher.fetch()

    _pp("data.go.kr 디딤돌", {
        "success": result.success,
        "error": result.error,
        "data": result.data,
        "raw_response": result.raw_response,
    })

    # data.go.kr는 실패할 수도 있음 (API 비활성, 점검 등)
    if not result.success:
        print(f"⚠️  data.go.kr 디딤돌 실패 (허용): {result.error}")


async def test_data_go_kr_bogeumjari():
    """data.go.kr 보금자리론 금리 API."""
    from app.config import settings
    if not settings.data_go_kr_service_key:
        pytest.skip("DATA_GO_KR_SERVICE_KEY 미설정")

    from app.fetchers.data_go_kr import BogeumjariFetcher

    fetcher = BogeumjariFetcher()
    result = await fetcher.fetch()

    _pp("data.go.kr 보금자리론", {
        "success": result.success,
        "error": result.error,
        "data": result.data,
        "raw_response": result.raw_response,
    })

    if not result.success:
        print(f"⚠️  data.go.kr 보금자리론 실패 (허용): {result.error}")


async def test_finlife():
    """금감원 finlife 은행 주담대 금리."""
    from app.config import settings
    if not settings.finlife_auth_key:
        pytest.skip("FINLIFE_AUTH_KEY 미설정")

    from app.fetchers.finlife import FinlifeFetcher

    fetcher = FinlifeFetcher()
    result = await fetcher.fetch()

    _pp("금감원 finlife", {
        "success": result.success,
        "error": result.error,
        "dcls_month": result.data.get("dcls_month") if result.data else None,
        "product_count": len(result.data.get("products", [])) if result.data else 0,
        "overall_avg_rate": result.data.get("overall_avg_rate") if result.data else None,
        "sample_products": result.data.get("products", [])[:3] if result.data else [],
    })

    assert result.success, f"finlife 실패: {result.error}"


async def test_ecos():
    """한국은행 ECOS 평균금리."""
    from app.config import settings
    if not settings.ecos_api_key:
        pytest.skip("ECOS_API_KEY 미설정")

    from app.fetchers.ecos import EcosFetcher

    fetcher = EcosFetcher()
    result = await fetcher.fetch()

    _pp("ECOS 평균금리", {
        "success": result.success,
        "error": result.error,
        "data": result.data,
    })

    assert result.success, f"ECOS 실패: {result.error}"
