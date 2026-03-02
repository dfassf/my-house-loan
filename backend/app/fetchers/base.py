"""Fetcher 기반 클래스."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class FetchResult:
    """API 수집 결과."""

    source: str
    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    raw_response: dict[str, Any] | None = None
    error: str = ""
    fetched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class BaseFetcher(ABC):
    """외부 금리 데이터 수집 기반 클래스."""

    @property
    @abstractmethod
    def source_name(self) -> str:
        """소스 식별자 (예: 'data_go_kr', 'finlife', 'ecos')."""

    @abstractmethod
    async def fetch(self) -> FetchResult:
        """외부 API에서 데이터를 가져와 파싱."""

    def _ok(self, data: dict[str, Any], raw: dict[str, Any] | None = None) -> FetchResult:
        return FetchResult(
            source=self.source_name,
            success=True,
            data=data,
            raw_response=raw,
        )

    def _fail(self, error: str) -> FetchResult:
        logger.warning("[%s] 수집 실패: %s", self.source_name, error)
        return FetchResult(
            source=self.source_name,
            success=False,
            error=error,
        )
