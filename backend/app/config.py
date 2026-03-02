from pathlib import Path

from pydantic_settings import BaseSettings

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    gemini_api_key: str = ""
    behind_proxy: bool = False
    database_url: str = ""
    llm_max_retries: int = 2
    llm_retry_delays: str = "1,2"
    llm_max_inflight: int = 24
    llm_acquire_timeout_ms: int = 1200
    llm_request_timeout_sec: int = 20
    cors_origins: str = ""
    intoss_app_name: str = ""

    # 외부 금리 데이터 API 키
    data_go_kr_service_key: str = ""
    finlife_auth_key: str = ""
    ecos_api_key: str = ""

    model_config = {
        "env_file": str(ENV_FILE),
        "extra": "ignore",
    }

    @property
    def parsed_cors_origins(self) -> list[str]:
        origins: list[str] = []

        for item in self.cors_origins.split(","):
            origin = item.strip().rstrip("/")
            if origin:
                origins.append(origin)

        app_name = self.intoss_app_name.strip()
        if app_name:
            origins.append(f"https://{app_name}.apps.tossmini.com")
            origins.append(f"https://{app_name}.private-apps.tossmini.com")

        deduped: list[str] = []
        seen: set[str] = set()
        for origin in origins:
            if origin in seen:
                continue
            seen.add(origin)
            deduped.append(origin)

        return deduped


settings = Settings()
