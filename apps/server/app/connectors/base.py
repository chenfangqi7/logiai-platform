from abc import ABC, abstractmethod


class BaseConnector(ABC):
    @abstractmethod
    async def test_connection(self) -> bool: ...

    @abstractmethod
    async def fetch_sample(self) -> list[dict]: ...

    @abstractmethod
    async def fetch_data(self) -> list[dict]: ...
