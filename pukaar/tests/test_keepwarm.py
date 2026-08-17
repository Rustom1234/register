"""The free-tier self-ping: on when deployed, silent everywhere else.

The failure this guards against is quiet in both directions — a pinger
that never fires leaves a dead-looking link in cold outreach email, and a
pinger that fires during tests reaches the network from CI.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from pukaar import keepwarm


def _env(monkeypatch, **kw):
    for k in ("PUKAAR_KEEPWARM", "PUKAAR_KEEPWARM_HOURS_UTC",
              "RENDER_EXTERNAL_URL"):
        monkeypatch.delenv(k, raising=False)
    for k, v in kw.items():
        monkeypatch.setenv(k, v)


# ---- when it wakes up ---------------------------------------------------

def test_silent_with_no_host_url(monkeypatch):
    # The local case: make run, and the whole test suite.
    _env(monkeypatch)
    assert keepwarm.target_url() is None
    assert keepwarm.start() is None


def test_render_url_is_the_whole_opt_in(monkeypatch):
    _env(monkeypatch, RENDER_EXTERNAL_URL="https://wayside.onrender.com")
    assert keepwarm.target_url() == "https://wayside.onrender.com/health"


def test_trailing_slash_does_not_double_up(monkeypatch):
    _env(monkeypatch, RENDER_EXTERNAL_URL="https://wayside.onrender.com/")
    assert keepwarm.target_url() == "https://wayside.onrender.com/health"


@pytest.mark.parametrize("off", ["0", "off", "false", "no", "OFF"])
def test_switching_it_off_beats_the_host_url(monkeypatch, off):
    _env(monkeypatch, RENDER_EXTERNAL_URL="https://wayside.onrender.com",
         PUKAAR_KEEPWARM=off)
    assert keepwarm.target_url() is None


def test_explicit_url_overrides_the_host(monkeypatch):
    _env(monkeypatch, RENDER_EXTERNAL_URL="https://wrong.example",
         PUKAAR_KEEPWARM="https://wayside.example")
    assert keepwarm.target_url() == "https://wayside.example/health"


def test_a_non_url_is_not_pinged(monkeypatch):
    # Someone setting PUKAAR_KEEPWARM=1 expecting a boolean must not make
    # us issue requests to "1/health".
    _env(monkeypatch, PUKAAR_KEEPWARM="1")
    assert keepwarm.target_url() is None


# ---- the hours it keeps -------------------------------------------------

def _at(hour: int) -> datetime:
    return datetime(2026, 8, 17, hour, 30, tzinfo=timezone.utc)


def test_default_window_covers_the_indian_day(monkeypatch):
    # 00:00-20:00 UTC is 05:30-01:30 IST.
    _env(monkeypatch)
    assert keepwarm.should_ping(_at(0))     # 05:30 IST
    assert keepwarm.should_ping(_at(12))    # 17:30 IST
    assert keepwarm.should_ping(_at(19))    # 00:30 IST, next day
    assert not keepwarm.should_ping(_at(20))   # 01:30 IST
    assert not keepwarm.should_ping(_at(23))   # 04:30 IST


def test_window_can_be_opened_to_the_full_day(monkeypatch):
    _env(monkeypatch, PUKAAR_KEEPWARM_HOURS_UTC="0-24")
    assert all(keepwarm.should_ping(_at(h)) for h in range(24))


def test_the_default_window_leaves_free_hours_in_hand(monkeypatch):
    # Render allows 750 instance-hours a month; a service awake every hour
    # of a 31-day month burns 744. The default must not sail that close.
    _env(monkeypatch)
    lo, hi = keepwarm.window()
    assert (hi - lo) * 31 < 700


@pytest.mark.parametrize("bad", ["", "garbage", "5", "20-3", "3-3",
                                 "-1-5", "0-25", "a-b"])
def test_a_broken_window_falls_back_rather_than_going_quiet(monkeypatch, bad):
    # Silently never pinging is the invisible failure: nobody notices until
    # a recipient reports the link hanging, weeks later.
    _env(monkeypatch, PUKAAR_KEEPWARM_HOURS_UTC=bad)
    assert keepwarm.window() == keepwarm.DEFAULT_HOURS


def test_ping_interval_beats_the_idle_timer():
    # Render sleeps a free service after ~15 idle minutes.
    assert keepwarm.PING_EVERY_S < 15 * 60


# ---- it must never take the app down ------------------------------------

def test_a_failing_ping_does_not_end_the_loop(monkeypatch):
    """A DNS blip ten minutes in must not silently stop all later pings."""
    calls: list[str] = []

    class FlakyClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, url):
            calls.append(url)
            if len(calls) == 1:
                raise OSError("dns went away")
            if len(calls) >= 3:
                raise asyncio.CancelledError
            return None

    import httpx
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: FlakyClient())
    monkeypatch.setattr(keepwarm, "should_ping", lambda now=None: True)

    async def run():
        with pytest.raises(asyncio.CancelledError):
            await keepwarm.loop("https://wayside.example/health", sleep_s=0)

    asyncio.run(run())
    assert len(calls) == 3, "loop stopped at the first failure"


def test_outside_the_window_it_sleeps_instead_of_pinging(monkeypatch):
    calls: list[str] = []

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, url):
            calls.append(url)

    import httpx
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: Client())
    monkeypatch.setattr(keepwarm, "should_ping", lambda now=None: False)

    async def run():
        # Let it go round several times, then stop it.
        task = asyncio.create_task(
            keepwarm.loop("https://wayside.example/health", sleep_s=0))
        await asyncio.sleep(0.05)
        task.cancel()

    asyncio.run(run())
    assert calls == []
