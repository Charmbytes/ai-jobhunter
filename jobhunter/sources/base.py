"""Base class for job sources. Add a new site by subclassing JobSource."""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import Filters, Job


class JobSource(ABC):
    name: str = "base"

    #: whether this source supports automated/assisted apply via Playwright
    supports_apply: bool = False

    @abstractmethod
    def fetch(self, filters: Filters, limit: int = 50) -> list[Job]:
        """Return raw listings matching the broad filters. Fine-grained
        filtering and scoring happen later in the matching engine."""
        raise NotImplementedError
