from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    alpaca_api_key: str = Field(default='', alias='ALPACA_API_KEY')
    alpaca_secret_key: str = Field(default='', alias='ALPACA_SECRET_KEY')
    alpaca_base_url: str = Field(default='https://paper-api.alpaca.markets', alias='ALPACA_BASE_URL')
    data_feed: str = Field(default='iex', alias='ALPACA_DATA_FEED')

    symbols: str = Field(default='AAPL,MSFT', alias='TRADE_SYMBOLS')
    bar_timeframe: str = Field(default='30Min', alias='BAR_TIMEFRAME')
    fast_ma_window: int = Field(default=5, alias='FAST_MA_WINDOW')
    slow_ma_window: int = Field(default=20, alias='SLOW_MA_WINDOW')

    max_position_pct: float = Field(default=0.10, alias='MAX_POSITION_PCT')
    max_daily_drawdown_pct: float = Field(default=0.05, alias='MAX_DAILY_DRAWDOWN_PCT')

    postgres_url: str = Field(
        default='postgresql+psycopg2://trader:trader@localhost:5432/trading',
        alias='POSTGRES_URL',
    )

    scheduler_timezone: str = Field(default='America/New_York', alias='SCHEDULER_TIMEZONE')

    @property
    def symbol_list(self) -> list[str]:
        return [s.strip().upper() for s in self.symbols.split(',') if s.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
