"""Fetcher 모듈 단위 테스트 (외부 API 호출 없이 파싱 로직 검증)."""

import pytest

from app.fetchers.data_go_kr import (
    _extract_items,
    _parse_bogeumjari_response,
    _parse_didimdol_response,
    _safe_float,
)
from app.fetchers.ecos import _parse_ecos_response
from app.fetchers.finlife import _parse_finlife_response
from app.fetchers.hf_scraper import (
    _amount_to_won,
    _parse_eligibility_page,
    _parse_news_list,
    _parse_rate_tables,
)


class TestSafeFloat:
    def test_string(self):
        assert _safe_float("3.14") == 3.14

    def test_int(self):
        assert _safe_float(5) == 5.0

    def test_none(self):
        assert _safe_float(None) is None

    def test_invalid(self):
        assert _safe_float("abc") is None


class TestExtractItems:
    def test_new_format(self):
        """신형 응답: body.item (단일 dict)."""
        raw = {"body": {"item": {"interest_10y_2000": "2.85"}}}
        assert _extract_items(raw) == [{"interest_10y_2000": "2.85"}]

    def test_old_format(self):
        """구형 응답: response.body.items.item (리스트)."""
        raw = {"response": {"body": {"items": {"item": [{"a": 1}]}}}}
        assert _extract_items(raw) == [{"a": 1}]

    def test_list_items(self):
        raw = {"response": {"body": {"items": [{"a": 1}]}}}
        assert _extract_items(raw) == [{"a": 1}]

    def test_empty(self):
        result = _extract_items({})
        assert result is None or result == []


class TestDidimdolParser:
    def test_real_api_response(self):
        """실제 data.go.kr 응답 형태 (2026)."""
        raw = {
            "header": {"resultCode": "00", "resultMsg": "정상"},
            "body": {
                "item": {
                    "interest_10y_2000": "2.85",
                    "interest_15y_2000": "2.95",
                    "interest_20y_2000": "3.05",
                    "interest_30y_2000": "3.10",
                    "interest_10y_4000": "3.20",
                    "interest_15y_4000": "3.30",
                    "interest_20y_4000": "3.40",
                    "interest_30y_4000": "3.45",
                    "interest_10y_6000": "3.55",
                    "interest_15y_6000": "3.65",
                    "interest_20y_6000": "3.75",
                    "interest_30y_6000": "3.80",
                    "applyDy": "20260301",
                },
                "pageNo": 1,
                "totalCount": 1,
                "numOfRows": 10,
            },
        }
        result = _parse_didimdol_response(raw)
        assert result is not None
        assert len(result["income_rate_tiers"]) == 3
        # 2천만 이하
        assert result["income_rate_tiers"][0]["max_income"] == 20_000_000
        assert result["income_rate_tiers"][0]["rate_10y"] == 2.85
        assert result["income_rate_tiers"][0]["rate_30y"] == 3.10
        # 4천만 이하
        assert result["income_rate_tiers"][1]["max_income"] == 40_000_000
        assert result["income_rate_tiers"][1]["rate_10y"] == 3.20
        # 6천만 이하
        assert result["income_rate_tiers"][2]["max_income"] == 60_000_000
        assert result["income_rate_tiers"][2]["rate_30y"] == 3.80
        assert result["effective_date"] == "2026-03-01"

    def test_old_format(self):
        """구형 응답 폴백."""
        raw = {
            "response": {
                "body": {
                    "items": {
                        "item": [
                            {
                                "incomeLevel": "20000000",
                                "loanRate10": "2.85",
                                "loanRate15": "2.95",
                                "loanRate20": "3.00",
                                "loanRate30": "3.10",
                                "effectiveDate": "2026-02-01",
                            },
                        ]
                    }
                }
            }
        }
        result = _parse_didimdol_response(raw)
        assert result is not None
        assert result["income_rate_tiers"][0]["rate_10y"] == 2.85

    def test_empty_items(self):
        raw = {"response": {"body": {"items": {"item": []}}}}
        assert _parse_didimdol_response(raw) is None


class TestBogeumjariParser:
    def test_new_format(self):
        """신형 응답: interest_Ny 패턴."""
        raw = {
            "body": {
                "item": {
                    "interest_10y": "4.05",
                    "interest_15y": "4.15",
                    "interest_20y": "4.25",
                    "interest_30y": "4.35",
                    "interest_40y": "4.40",
                    "interest_50y": "4.45",
                    "applyDy": "20260301",
                }
            }
        }
        result = _parse_bogeumjari_response(raw)
        assert result is not None
        assert len(result["income_rate_tiers"]) == 1
        assert result["income_rate_tiers"][0]["rate_10y"] == 4.05
        assert result["income_rate_tiers"][0]["rate_50y"] == 4.45
        assert result["income_rate_tiers"][0]["max_income"] == 70_000_000
        assert result["effective_date"] == "2026-03-01"

    def test_old_format(self):
        """구형 응답: loanRateN 패턴."""
        raw = {
            "response": {
                "body": {
                    "items": {
                        "item": [
                            {
                                "loanRate10": "4.05",
                                "loanRate30": "4.35",
                                "effectiveDate": "2026-03-01",
                            }
                        ]
                    }
                }
            }
        }
        result = _parse_bogeumjari_response(raw)
        assert result is not None
        assert result["income_rate_tiers"][0]["rate_30y"] == 4.35
        assert result["income_rate_tiers"][0]["max_income"] == 70_000_000


class TestEcosParser:
    def test_valid_response(self):
        raw = {
            "StatisticSearch": {
                "row": [
                    {"TIME": "202401", "DATA_VALUE": "3.99"},
                    {"TIME": "202402", "DATA_VALUE": "3.95"},
                    {"TIME": "202403", "DATA_VALUE": "3.92"},
                ]
            }
        }
        result = _parse_ecos_response(raw)
        assert result is not None
        assert len(result["monthly_rates"]) == 3
        assert result["latest_month"] == "202403"
        assert result["latest_rate"] == 3.92

    def test_empty_rows(self):
        raw = {"StatisticSearch": {"row": []}}
        assert _parse_ecos_response(raw) is None

    def test_no_stat_search(self):
        assert _parse_ecos_response({}) is None


class TestFinlifeParser:
    def test_valid_response(self):
        raw = {
            "result": {
                "baseList": [
                    {
                        "fin_prdt_cd": "P001",
                        "kor_co_nm": "KB국민은행",
                        "fin_prdt_nm": "KB주택담보대출",
                        "dcls_month": "202602",
                    }
                ],
                "optionList": [
                    {
                        "fin_prdt_cd": "P001",
                        "mrtg_type": "A",
                        "rpay_type": "D",
                        "lend_rate_type": "C",
                        "lend_rate_min": "3.50",
                        "lend_rate_max": "4.20",
                        "lend_rate_avg": "3.85",
                    },
                    {
                        "fin_prdt_cd": "P001",
                        "mrtg_type": "A",
                        "rpay_type": "D",
                        "lend_rate_type": "F",
                        "lend_rate_min": "4.00",
                        "lend_rate_max": "4.50",
                        "lend_rate_avg": "4.25",
                    },
                ],
            }
        }
        result = _parse_finlife_response(raw)
        assert result is not None
        assert result["dcls_month"] == "202602"
        assert len(result["products"]) == 2
        assert result["sample_count"] == 2
        # 평균: (3.85 + 4.25) / 2 = 4.05
        assert result["overall_avg_rate"] == 4.05

    def test_empty_options(self):
        raw = {"result": {"baseList": [], "optionList": []}}
        assert _parse_finlife_response(raw) is None


class TestHfScraper:
    def test_parse_rates_from_html(self):
        html = """
        <html>
        <body>
        <h3>디딤돌대출 금리안내</h3>
        <p>적용일: 2026.02.01 기준</p>
        <table>
            <tr><td>2천만원 이하</td><td>2.85%</td><td>2.95%</td><td>3.00%</td><td>3.10%</td></tr>
            <tr><td>4천만원 이하</td><td>3.20%</td><td>3.30%</td><td>3.35%</td><td>3.45%</td></tr>
        </table>
        </body>
        </html>
        """
        result = _parse_rate_tables(html)
        assert result is not None
        assert result["rate_min"] == 2.85
        assert result["rate_max"] == 3.45
        assert result["effective_date"] == "2026-02-01"
        assert result["raw_rate_count"] == 8

    def test_no_rates(self):
        html = "<html><body>금리 정보 없음</body></html>"
        assert _parse_rate_tables(html) is None


class TestAmountToWon:
    def test_억(self):
        assert _amount_to_won("5", "억") == 500_000_000

    def test_만(self):
        assert _amount_to_won("7000", "만") == 70_000_000

    def test_천만(self):
        assert _amount_to_won("8500", "만") == 85_000_000

    def test_comma(self):
        assert _amount_to_won("4,500", "만") == 45_000_000


class TestEligibilityParser:
    def test_didimdol_page(self):
        html = """
        <html><body>
        <h3>디딤돌대출 상품안내</h3>
        <p>대상주택: 주택가격 5억원 이하 (신혼 6억원 이하)</p>
        <p>대출한도: 2.5억원 이내</p>
        <p>소득요건: 부부합산 연소득 6,000만원 이하 (신혼 8,500만원 이하)</p>
        <p>순자산 4.5억원 이하</p>
        <p>전용면적 85㎡ 이하 (수도권 100㎡)</p>
        <p>무주택 세대주</p>
        <p>LTV 70% (생애최초 80%)</p>
        </body></html>
        """
        result = _parse_eligibility_page(html, "didimdol")
        assert result is not None
        assert result["max_housing_price"] == 500_000_000
        assert result["max_housing_price_newlywed"] == 600_000_000
        assert result["max_net_assets"] == 450_000_000
        assert result["max_area_m2"] == 85
        assert result["max_area_m2_urban"] == 100
        assert result["requires_homeless"] is True
        assert 70 in result["ltv_values"]
        assert 80 in result["ltv_values"]

    def test_empty_page(self):
        html = "<html><body>상품 설명 없음</body></html>"
        assert _parse_eligibility_page(html, "didimdol") is None


class TestNewsParser:
    def test_valid_news_list(self):
        html = """
        <html><body>
        <a href="/ko/sub05/sub05_04_05.do?mode=view&articleNo=599691">
        2026년 2월 보금자리론 금리 인상 안내
        </a>
        <a href="/ko/sub05/sub05_04_05.do?mode=view&articleNo=599610">
        디딤돌대출 자격요건 변경 안내
        </a>
        <a href="/ko/sub05/sub05_04_05.do?mode=view&articleNo=599500">
        한국주택금융공사 조직개편 안내
        </a>
        </body></html>
        """
        result = _parse_news_list(html)
        assert result is not None
        assert len(result) == 3

        # 보금자리+금리+인상 → 관련 기사
        assert result[0]["is_relevant"] is True
        assert "보금자리" in result[0]["keywords_matched"]
        assert "금리" in result[0]["keywords_matched"]

        # 디딤돌+자격요건+변경 → 관련 기사
        assert result[1]["is_relevant"] is True

        # 조직개편 → 비관련
        assert result[2]["is_relevant"] is False

    def test_empty_page(self):
        html = "<html><body>목록 없음</body></html>"
        assert _parse_news_list(html) is None
