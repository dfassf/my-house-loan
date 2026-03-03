"""인메모리 캐시 저장소.

서버 시작 시 초기화되며, 스케줄러가 주기적으로 갱신합니다.
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class FetchLogEntry:
    source: str
    status: str  # "success" | "fail" | "alert"
    message: str = ""
    fetched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class HfNewsEntry:
    article_id: str
    title: str
    is_relevant: bool
    keywords_matched: str = ""
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged: bool = False


@dataclass
class PolicyProductEntry:
    product_id: str
    product_data: dict[str, Any]
    source: str = "manual"
    rate_updated_at: datetime | None = None
    eligibility_updated_at: datetime | None = None
    discount_updated_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class InMemoryCache:
    """서버 전체에서 단일 인스턴스로 사용하는 인메모리 캐시."""

    def __init__(self) -> None:
        self.policy_products: dict[str, PolicyProductEntry] = {}
        self.bank_rates: list[dict[str, Any]] = []
        self.bank_avg_rates: dict[str, float] = {}
        self.hf_news: dict[str, HfNewsEntry] = {}
        self.fetch_last_success: dict[str, datetime] = {}
        self.fetch_logs: deque[FetchLogEntry] = deque(maxlen=100)

    def log_fetch(self, source: str, status: str, message: str = "") -> None:
        entry = FetchLogEntry(source=source, status=status, message=message)
        self.fetch_logs.appendleft(entry)
        if status == "success":
            self.fetch_last_success[source] = entry.fetched_at

    def get_last_fetch_time(self, source: str) -> datetime | None:
        return self.fetch_last_success.get(source)

    def get_latest_avg_rate(self) -> float | None:
        if not self.bank_avg_rates:
            return None
        latest_month = max(self.bank_avg_rates.keys())
        return self.bank_avg_rates[latest_month]

    def get_latest_avg_entry(self) -> dict[str, Any] | None:
        if not self.bank_avg_rates:
            return None
        latest_month = max(self.bank_avg_rates.keys())
        return {"stat_month": latest_month, "rate_value": self.bank_avg_rates[latest_month]}

    def get_product_data(self, product_id: str) -> dict[str, Any] | None:
        entry = self.policy_products.get(product_id)
        return entry.product_data if entry is not None else None


cache = InMemoryCache()
