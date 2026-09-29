import httpx
import pytest

from app.connectors.rest import RestApiConnector


@pytest.mark.asyncio
async def test_post_pagination_query_and_incremental_checkpoint():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        page = int(__import__("json").loads(request.content)["page"])
        items = [{"waybillNo": f"P-{number}"} for number in range((page - 1) * 2 + 1, min(page * 2, 3) + 1)]
        return httpx.Response(200, json={"data": {"items": items}, "total": 3}, headers={"content-type": "application/json"})

    adapter = RestApiConnector("http://localhost:8000/mock", {
        "method": "POST", "items_path": "data.items", "query_params": {"customer": "demo"},
        "request_body": {"category": "shipment"},
        "sync_mode": "INCREMENTAL", "incremental_field": "updatedAt", "incremental_param": "since", "last_sync_value": "2026-09-28T08:00:00Z",
        "pagination": {"type": "PAGE_NUMBER", "location": "body", "page_size": 2, "max_pages": 5, "total_path": "total"},
    }, "none", transport=httpx.MockTransport(handler))
    rows = await adapter.fetch_data()
    assert len(rows) == 3 and len(requests) == 2
    assert requests[0].method == "POST"
    assert requests[0].url.params["customer"] == "demo"
    assert requests[0].url.params["since"] == "2026-09-28T08:00:00Z"
    assert adapter.last_response_meta["status_code"] == 200
    assert len(await adapter.fetch_sample()) == 2


def test_rest_config_rejects_unbounded_timeout_and_unsafe_header():
    with pytest.raises(ValueError, match="timeout"):
        RestApiConnector("http://localhost:8000/mock", {"timeout_seconds": 0})
    with pytest.raises(ValueError, match="header"):
        RestApiConnector("http://localhost:8000/mock", {"header_name": "Host", "header_value": "secret"}, "header")._headers()
    with pytest.raises(ValueError, match="GET connectors cannot"):
        RestApiConnector("http://localhost:8000/mock", {"pagination": {"type": "PAGE_NUMBER", "location": "body"}})


@pytest.mark.asyncio
async def test_pagination_limit_fails_instead_of_reporting_truncated_success():
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"items": [{"waybillNo": "1"}]}))
    adapter = RestApiConnector("http://localhost:8000/mock", {"items_path": "items",
        "pagination": {"type": "PAGE_NUMBER", "page_size": 1, "max_pages": 1}}, transport=transport)
    with pytest.raises(ValueError, match="page limit"):
        await adapter.fetch_data()


@pytest.mark.asyncio
async def test_get_without_pagination_returns_single_page():
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=[{"waybillNo": "A"}]))
    adapter = RestApiConnector("http://localhost:8000/mock", {}, transport=transport)
    assert await adapter.fetch_data() == [{"waybillNo": "A"}]


@pytest.mark.asyncio
async def test_url_query_is_preserved_when_config_has_no_query_params():
    seen: list[str] = []
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.params["prefix"])
        return httpx.Response(200, json=[{"waybillNo": "P-1"}])
    adapter = RestApiConnector("http://localhost:8000/mock?prefix=ACPT", {}, transport=httpx.MockTransport(handler))
    assert await adapter.fetch_data() == [{"waybillNo": "P-1"}]
    assert seen == ["ACPT"]
