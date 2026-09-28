from app.connectors.base import BaseConnector


class WebhookConnector(BaseConnector):
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows

    async def test_connection(self) -> bool:
        return bool(self.rows)

    async def fetch_sample(self) -> list[dict]:
        return self.rows[:5]

    async def fetch_data(self) -> list[dict]:
        return self.rows
