"""스케줄러용 HF 보도자료 모니터링."""

from __future__ import annotations

import logging
from typing import Any

from app.cache import HfNewsEntry, cache
from app.fetchers.hf_scraper import HfNewsScraper


async def monitor_hf_news(logger: logging.Logger) -> list[dict[str, Any]]:
    """HF 보도자료 크롤링 후 신규 관련 기사를 감지."""
    fetcher = HfNewsScraper()
    result = await fetcher.fetch()

    if not result.success:
        cache.log_fetch(fetcher.source_name, "fail", result.error)
        return []

    articles = result.data.get("articles", [])
    new_alerts: list[dict[str, Any]] = []

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
            "hf_news",
            "alert",
            f"{len(new_alerts)}건 관련 기사 감지: {[a['title'] for a in new_alerts]}",
        )
    else:
        cache.log_fetch("hf_news", "success", f"{len(articles)}건 확인, 새 알림 없음")

    return new_alerts
