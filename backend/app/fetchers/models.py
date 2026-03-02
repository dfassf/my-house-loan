"""금리 + 자격요건 캐시 DB 모델."""

from datetime import datetime, timezone

from sqlalchemy import (
    DATE,
    Boolean,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class PolicyProductCache(Base):
    """정책대출 전체 상품 데이터 캐시 (자격요건 + 금리 + 우대조건).

    rate_data, eligibility_data, discount_data를 분리 저장하여
    각각 독립적으로 갱신 가능.
    """

    __tablename__ = "policy_product_cache"
    __table_args__ = (
        UniqueConstraint("product_id", name="uq_policy_product"),
        Index("ix_policy_product_id", "product_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_id: Mapped[str] = mapped_column(String(30))

    # 전체 상품 데이터 (JSON 파일과 동일 구조)
    product_data: Mapped[dict] = mapped_column(JSONB)

    # 개별 섹션별 마지막 갱신 시각 (어떤 부분이 오래된지 추적)
    rate_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    eligibility_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    discount_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # 메타
    source: Mapped[str] = mapped_column(String(50), default="manual")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class BankRateCache(Base):
    """은행 주담대 금리 캐시 (finlife 개별 상품)."""

    __tablename__ = "bank_rate_cache"
    __table_args__ = (
        UniqueConstraint(
            "dcls_month", "fin_co_nm", "fin_prdt_nm",
            "mrtg_type", "rpay_type", "lend_rate_type",
            name="uq_bank_rate",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    dcls_month: Mapped[str] = mapped_column(String(6))
    fin_co_nm: Mapped[str] = mapped_column(String(100))
    fin_prdt_nm: Mapped[str] = mapped_column(String(200))
    mrtg_type: Mapped[str] = mapped_column(String(1))
    rpay_type: Mapped[str] = mapped_column(String(1))
    lend_rate_type: Mapped[str] = mapped_column(String(1))
    rate_min: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    rate_max: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    rate_avg: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


class BankAvgRateCache(Base):
    """은행 평균금리 캐시 (ECOS)."""

    __tablename__ = "bank_avg_rate_cache"
    __table_args__ = (
        UniqueConstraint("stat_month", name="uq_bank_avg_month"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    stat_month: Mapped[str] = mapped_column(String(6))
    rate_value: Mapped[float] = mapped_column(Numeric(5, 2))
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


class HfNewsWatch(Base):
    """HF 보도자료/공지사항 모니터링 기록."""

    __tablename__ = "hf_news_watch"
    __table_args__ = (
        UniqueConstraint("article_id", name="uq_hf_news_article"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    article_id: Mapped[str] = mapped_column(String(20))
    title: Mapped[str] = mapped_column(String(500))
    is_relevant: Mapped[bool] = mapped_column(Boolean, default=False)
    keywords_matched: Mapped[str] = mapped_column(Text, default="")
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)


class RateFetchLog(Base):
    """데이터 수집 이력 로그."""

    __tablename__ = "rate_fetch_log"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(10))
    message: Mapped[str] = mapped_column(Text, default="")
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
