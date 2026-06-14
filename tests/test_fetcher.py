from datetime import datetime, timezone

import pandas as pd
import pytest

from options_mm.data.fetcher import CacheEntry, DataFetcher


def test_fetcher_returns_cached_rfr_when_fresh():
    fetcher = DataFetcher(poll_interval_seconds=60, fred_api_key="unused")
    fetcher._cache[("rfr", fetcher.fred_series_id)] = CacheEntry(
        value=0.042,
        fetched_at=datetime.now(timezone.utc),
    )

    assert fetcher.get_rfr() == 0.042


def test_fetcher_uses_default_rfr_without_fred_key():
    fetcher = DataFetcher(fred_api_key="", default_rfr=0.037)

    assert fetcher.get_rfr() == 0.037


def test_fetcher_interpolates_replay_spot_between_minute_bars(monkeypatch):
    fetcher = DataFetcher()
    index = pd.DatetimeIndex(
        [
            "2026-06-12 13:30:00+00:00",
            "2026-06-12 13:31:00+00:00",
        ]
    )
    history = pd.DataFrame({"Close": [100.0, 101.0]}, index=index)
    monkeypatch.setattr(fetcher, "get_history", lambda *args, **kwargs: history)

    spot = fetcher.get_replay_spot(
        "SPY",
        datetime(2026, 6, 12, 13, 30, 30, tzinfo=timezone.utc),
    )

    assert spot == pytest.approx(100.5)
