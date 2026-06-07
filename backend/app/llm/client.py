"""Gemini LLM 클라이언트 — hakamaka 패턴 기반."""

import asyncio
import logging
from collections.abc import Awaitable, Callable

from google import genai

from app.config import settings

logger = logging.getLogger(__name__)

MODEL = "gemini-3.1-flash-lite"

MAX_RETRIES = max(0, settings.llm_max_retries)
MAX_INFLIGHT = max(1, settings.llm_max_inflight)
ACQUIRE_TIMEOUT_SEC = max(0, settings.llm_acquire_timeout_ms) / 1000
REQUEST_TIMEOUT_SEC = max(1, settings.llm_request_timeout_sec)

_llm_semaphore = asyncio.Semaphore(MAX_INFLIGHT)


def _parse_retry_delays(raw: str, max_retries: int) -> list[int]:
    parsed: list[int] = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            parsed.append(max(0, int(item)))
        except ValueError:
            continue
    if not parsed:
        parsed = [1]
    if max_retries > 0 and len(parsed) < max_retries:
        parsed.extend([parsed[-1]] * (max_retries - len(parsed)))
    return parsed


RETRY_DELAYS = _parse_retry_delays(settings.llm_retry_delays, MAX_RETRIES)


class LLMOverloadedError(RuntimeError):
    pass


class LLMRequestTimeoutError(RuntimeError):
    pass


def get_client(api_key: str) -> genai.Client:
    return genai.Client(api_key=api_key)


async def call_with_limits(fn: Callable[[], Awaitable[str]], label: str) -> str:
    """동시 호출 제한 + 타임아웃 적용."""
    try:
        await asyncio.wait_for(_llm_semaphore.acquire(), timeout=ACQUIRE_TIMEOUT_SEC)
    except asyncio.TimeoutError as exc:
        logger.warning(f"[{label}] 슬롯 획득 실패")
        raise LLMOverloadedError("요청이 많아서 잠시 기다려 주세요.") from exc

    try:
        return await asyncio.wait_for(fn(), timeout=REQUEST_TIMEOUT_SEC)
    except asyncio.TimeoutError as exc:
        logger.warning(f"[{label}] LLM 타임아웃 ({REQUEST_TIMEOUT_SEC}s)")
        raise LLMRequestTimeoutError("응답 시간이 너무 오래 걸렸어요.") from exc
    finally:
        _llm_semaphore.release()


async def retry(fn: Callable[[], Awaitable[str]], label: str) -> str:
    """재시도 래퍼."""
    last_err: Exception | None = None

    for attempt in range(MAX_RETRIES + 1):
        try:
            return await fn()
        except LLMOverloadedError:
            raise
        except Exception as exc:
            last_err = exc
            if attempt >= MAX_RETRIES:
                logger.error(f"[{label}] {MAX_RETRIES + 1}회 시도 모두 실패: {exc}")
                continue
            delay = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)]
            logger.warning(f"[{label}] 시도 {attempt + 1} 실패: {exc}, {delay}초 후 재시도")
            await asyncio.sleep(delay)

    if last_err is None:
        raise RuntimeError(f"[{label}] 알 수 없는 오류")
    raise last_err
