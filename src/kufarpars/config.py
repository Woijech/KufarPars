"""Application configuration loaded from environment and ``.env``.

Every setting used by the parser, CLI, or bot should live here so deployment
differences stay outside the business logic.
"""

from dataclasses import dataclass
from os import getenv

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Runtime settings for KufarPars."""

    base_url: str = getenv("KUFARPARS_BASE_URL", "https://www.kufar.by")
    realty_url: str = getenv("KUFARPARS_REALTY_URL", "https://re.kufar.by")
    timeout_seconds: float = float(getenv("KUFARPARS_TIMEOUT_SECONDS", "20"))
    request_retries: int = int(getenv("KUFARPARS_REQUEST_RETRIES", "2"))
    request_retry_delay_seconds: float = float(
        getenv("KUFARPARS_REQUEST_RETRY_DELAY_SECONDS", "2")
    )
    user_agent: str = getenv(
        "KUFARPARS_USER_AGENT",
        "KufarPars/0.1 (+local research parser)",
    )
    telegram_bot_token: str | None = getenv("TELEGRAM_BOT_TOKEN")
    bot_db_path: str = getenv(
        "KUFARPARS_BOT_DB_PATH",
        "data/kufarpars.sqlite3",
    )
    legacy_bot_state_path: str | None = getenv(
        "KUFARPARS_LEGACY_BOT_STATE_PATH",
        "data/kufarpars_bot_state.json",
    )
    seen_ttl_days: int = int(getenv("KUFARPARS_SEEN_TTL_DAYS", "60"))
    max_seen_per_chat: int = int(getenv("KUFARPARS_MAX_SEEN_PER_CHAT", "5000"))
    bot_poll_interval_seconds: float = float(
        getenv("KUFARPARS_BOT_POLL_INTERVAL_SECONDS", "300")
    )
    bot_initial_poll_delay_seconds: float = float(
        getenv("KUFARPARS_BOT_INITIAL_POLL_DELAY_SECONDS", "10")
    )
    bot_max_notifications_per_check: int = int(
        getenv("KUFARPARS_BOT_MAX_NOTIFICATIONS_PER_CHECK", "5")
    )
    bot_fetch_timeout_seconds: float = float(
        getenv("KUFARPARS_BOT_FETCH_TIMEOUT_SECONDS", "8")
    )
    bot_fetch_retries: int = int(getenv("KUFARPARS_BOT_FETCH_RETRIES", "1"))
    bot_fetch_retry_delay_seconds: float = float(
        getenv("KUFARPARS_BOT_FETCH_RETRY_DELAY_SECONDS", "1")
    )
    bot_max_pages: int = int(getenv("KUFARPARS_BOT_MAX_PAGES", "1"))
    bot_page_delay_seconds: float = float(
        getenv("KUFARPARS_BOT_PAGE_DELAY_SECONDS", "1")
    )
    bot_max_images: int = int(getenv("KUFARPARS_BOT_MAX_IMAGES", "3"))


settings = Settings()
