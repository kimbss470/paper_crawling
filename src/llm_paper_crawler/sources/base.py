from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import Paper


class BaseCrawler(ABC):
    @abstractmethod
    def fetch_many(self, years: list[int]) -> list[Paper]:
        raise NotImplementedError
