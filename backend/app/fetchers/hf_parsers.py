"""HF 스크래핑 HTML 파서 모음."""

from __future__ import annotations

import re
from typing import Any

_ALERT_KEYWORDS = [
    "디딤돌", "보금자리", "금리", "대출한도", "소득기준", "자산기준",
    "LTV", "DSR", "주택가격", "순자산", "면적", "우대", "생애최초",
    "신혼", "다자녀", "자격요건", "개편", "개선", "인상", "인하", "변경",
]


def _parse_rate_tables(html: str) -> dict[str, Any] | None:
    """HTML에서 금리 숫자를 추출."""
    rate_pattern = re.compile(r"(\d+\.\d{1,2})\s*%")
    rates = [float(m.group(1)) for m in rate_pattern.finditer(html)]

    if not rates:
        return None

    date_pattern = re.compile(r"(\d{4})[.\-년]\s*(\d{1,2})[.\-월]\s*(\d{1,2})")
    date_match = date_pattern.search(html)
    effective_date = ""
    if date_match:
        y, m, d = date_match.groups()
        effective_date = f"{y}-{int(m):02d}-{int(d):02d}"

    valid_rates = [r for r in rates if 0.5 <= r <= 10.0]

    return {
        "rates_found": valid_rates,
        "rate_min": min(valid_rates) if valid_rates else None,
        "rate_max": max(valid_rates) if valid_rates else None,
        "effective_date": effective_date,
        "raw_rate_count": len(valid_rates),
    }


def _parse_eligibility_page(html: str, product_id: str) -> dict[str, Any] | None:
    """상품안내 페이지에서 자격요건 추출."""
    del product_id
    result: dict[str, Any] = {}

    amounts = _extract_amounts(html)
    if not amounts:
        return None

    result["amounts_found"] = amounts

    price_pattern = re.compile(r"주택가격[^0-9]*(\d[\d,.]*)\s*(억|만)")
    price_match = price_pattern.search(html)
    if price_match:
        result["max_housing_price"] = _amount_to_won(price_match.group(1), price_match.group(2))

    loan_pattern = re.compile(r"대출한도[^0-9]*(\d[\d,.]*)\s*(억|만)")
    loan_match = loan_pattern.search(html)
    if loan_match:
        result["max_loan_amount"] = _amount_to_won(loan_match.group(1), loan_match.group(2))

    income_patterns = [
        re.compile(r"(?:연소득|부부합산[^0-9]*)(\d[\d,.]*)\s*(억|만)\s*원?\s*이하"),
        re.compile(r"소득[^0-9]*(\d[\d,.]*)\s*(억|만)\s*원?\s*이하"),
    ]
    for pat in income_patterns:
        match = pat.search(html)
        if match:
            result["max_income"] = _amount_to_won(match.group(1), match.group(2))
            break

    asset_pattern = re.compile(r"순자산[^0-9]*(\d[\d,.]*)\s*(억|만)\s*원?\s*이하")
    asset_match = asset_pattern.search(html)
    if asset_match:
        result["max_net_assets"] = _amount_to_won(asset_match.group(1), asset_match.group(2))

    area_pattern = re.compile(r"(\d{2,3})\s*[㎡m²]")
    area_matches = area_pattern.findall(html)
    if area_matches:
        areas = [int(a) for a in area_matches if 30 <= int(a) <= 200]
        if areas:
            result["max_area_m2"] = min(areas)
            if len(areas) > 1:
                result["max_area_m2_urban"] = max(areas)

    ltv_section = re.search(r"LTV.{0,100}", html, re.DOTALL)
    if ltv_section:
        pct_pattern = re.compile(r"(\d{2,3})%")
        ltv_matches = pct_pattern.findall(ltv_section.group(0))
        if ltv_matches:
            result["ltv_values"] = [int(v) for v in ltv_matches if 30 <= int(v) <= 100]

    result["requires_homeless"] = "무주택" in html

    newlywed_price_patterns = [
        re.compile(r"신혼[^0-9]*주택가격[^0-9]*(\d[\d,.]*)\s*(억|만)"),
        re.compile(r"신혼[^0-9]{0,5}(\d[\d,.]*)\s*(억)\s*원?\s*이하"),
    ]
    for pat in newlywed_price_patterns:
        nw_match = pat.search(html)
        if nw_match:
            result["max_housing_price_newlywed"] = _amount_to_won(nw_match.group(1), nw_match.group(2))
            break

    newlywed_income_patterns = [
        re.compile(r"신혼[^0-9]*소득[^0-9]*(\d[\d,.]*)\s*(억|만)"),
        re.compile(r"신혼[^0-9]{0,5}(\d[\d,.]*)\s*(만)\s*원?\s*이하"),
    ]
    for pat in newlywed_income_patterns:
        ni_match = pat.search(html)
        if ni_match:
            result["max_income_newlywed"] = _amount_to_won(ni_match.group(1), ni_match.group(2))
            break

    return result


def _extract_amounts(html: str) -> list[dict[str, Any]]:
    """HTML에서 금액 표현 추출 (N억원, N천만원 등)."""
    pattern = re.compile(r"(\d[\d,.]*)\s*(억|천만|만)\s*원")
    results = []
    for match in pattern.finditer(html):
        num_str = match.group(1).replace(",", "")
        unit = match.group(2)
        try:
            value = _amount_to_won(num_str, unit)
            results.append({"raw": match.group(0), "won": value})
        except ValueError:
            continue
    return results


def _amount_to_won(num_str: str, unit: str) -> int:
    """'5억' → 500000000, '7000만' → 70000000."""
    num = float(num_str.replace(",", ""))
    if unit == "억":
        return int(num * 100_000_000)
    if unit == "천만":
        return int(num * 10_000_000)
    if unit == "만":
        return int(num * 10_000)
    return int(num)


def _parse_news_list(html: str) -> list[dict[str, Any]] | None:
    """보도자료 목록에서 기사 제목 + ID 추출."""
    article_pattern = re.compile(r'articleNo=(\d+)[^>]*>([^<]+)<')
    matches = article_pattern.findall(html)

    if not matches:
        alt_pattern = re.compile(
            r'<a[^>]*href=["\'][^"\']*articleNo=(\d+)[^"\']*["\'][^>]*>\s*([^<]+?)\s*</a>',
        )
        matches = alt_pattern.findall(html)

    if not matches:
        return None

    articles: list[dict[str, Any]] = []
    for article_id, title in matches:
        title = title.strip()
        if not title:
            continue

        matched_keywords = [keyword for keyword in _ALERT_KEYWORDS if keyword in title]
        is_relevant = len(matched_keywords) >= 2

        articles.append({
            "article_id": article_id,
            "title": title,
            "is_relevant": is_relevant,
            "keywords_matched": matched_keywords,
        })

    return articles
