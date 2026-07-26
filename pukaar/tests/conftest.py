import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from pukaar.config import Config
from pukaar.db import Store
from pukaar.service import PukaarService


class Clock:
    # Default to 10:00 sim time — inside the dispatch window; night-mode
    # tests set their own hour explicitly.
    def __init__(self, t: float = 10 * 3600.0):
        self.t = t

    def __call__(self) -> float:
        return self.t

    def advance(self, dt: float) -> None:
        self.t += dt


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def cfg() -> Config:
    c = Config()
    c.backend = "mock"
    return c


@pytest.fixture
def svc(cfg, clock) -> PukaarService:
    return PukaarService(cfg, Store(":memory:"), now_fn=clock)
