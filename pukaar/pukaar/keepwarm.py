"""Stop the free-tier host from falling asleep under the outreach link.

Render's free plan spins a service down after ~15 idle minutes, and the
next visitor then stares at a blank tab for 20-60s while it boots. That is
survivable for a demo you are standing next to and fatal for a cold email:
the `/film` link goes to people who have never heard of us, and a link that
appears broken is a link that gets closed.

The usual fix is an external cron service pinging `/health`. This does the
same thing from inside the process, so a fresh deploy needs nothing set up
by hand — the ping leaves the container, comes back through the host's
router, and reads as ordinary traffic, which is what the idle timer counts.

Two things it deliberately does *not* do:

* **It does not run 24/7 by default.** Free hosting bills instance-hours
  (Render allows 750/month) and a service kept awake every hour of a
  31-day month burns 744 of them — inside the allowance, but with no room
  for a second service or a bad month. The default window is 00:00-20:00
  UTC, which is 05:30-01:30 in Delhi: every waking hour a recipient in
  India or Nepal might plausibly click, for ~600 hours a month. The cost
  is that the first visitor after the overnight gap still pays the cold
  start. Set `PUKAAR_KEEPWARM_HOURS_UTC=0-24` to take that last one too,
  if you know the allowance is free for it.
* **It does not turn itself on locally.** It wakes only where a host has
  told us our own public URL, so `make run` and the test suite never
  reach the network.
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone

# Comfortably under the ~15 minute idle timer even if a ping is slow or
# lost, without hammering a host we are already getting for free.
PING_EVERY_S = 10 * 60

# Hours are UTC and half-open: 0-20 means 00:00 <= t < 20:00.
DEFAULT_HOURS = (0, 20)


def target_url() -> str | None:
    """The URL to ping, or None when this process should stay quiet.

    `RENDER_EXTERNAL_URL` is injected by Render itself, so being deployed
    is the whole opt-in. `PUKAAR_KEEPWARM` overrides in both directions:
    a falsy value switches it off, any other value is used as the URL, so
    the same code works on a host that names its own URL differently.
    """
    override = os.environ.get("PUKAAR_KEEPWARM", "").strip()
    if override.lower() in {"0", "off", "false", "no"}:
        return None
    base = override or os.environ.get("RENDER_EXTERNAL_URL", "").strip()
    if not base.startswith(("http://", "https://")):
        return None
    return base.rstrip("/") + "/health"


def window() -> tuple[int, int]:
    """The (start, end) UTC hours to ping between, half-open."""
    raw = os.environ.get("PUKAAR_KEEPWARM_HOURS_UTC", "").strip()
    if not raw:
        return DEFAULT_HOURS
    try:
        lo_s, hi_s = raw.split("-", 1)
        lo, hi = int(lo_s), int(hi_s)
    except ValueError:
        return DEFAULT_HOURS
    # A malformed window must not silently mean "never ping" — that failure
    # is invisible until someone reports a dead link weeks later.
    if not (0 <= lo < hi <= 24):
        return DEFAULT_HOURS
    return lo, hi


def should_ping(now: datetime | None = None) -> bool:
    lo, hi = window()
    hour = (now or datetime.now(timezone.utc)).hour
    return lo <= hour < hi


async def loop(url: str, *, sleep_s: float = PING_EVERY_S) -> None:
    """Ping forever. Never raises — a dead pinger must not kill the app."""
    import httpx

    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            await asyncio.sleep(sleep_s)
            if not should_ping():
                continue
            try:
                await client.get(url)
            except Exception:
                # Offline, DNS blip, host restarting — all self-correcting
                # ten minutes from now, and none of them worth a stack
                # trace in the log of a service that is otherwise healthy.
                pass


def start(loop_fn=loop) -> asyncio.Task | None:
    """Start the pinger if this deploy wants one. Returns the task, or None."""
    url = target_url()
    if url is None:
        return None
    return asyncio.create_task(loop_fn(url))
