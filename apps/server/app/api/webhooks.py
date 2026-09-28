import hmac
import json

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.connectors.webhook import WebhookConnector
from app.models.domain import Connector
from app.repositories.connector import ConnectorRepository
from app.services.shipments import ShipmentService
from app.tasks.exception_analysis import analyze_new_exceptions

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])


@router.post("/{connector_id}")
async def receive_webhook(connector_id: str, request: Request, background_tasks: BackgroundTasks, x_webhook_secret: str = Header(""), session: AsyncSession = Depends(get_session)):
    item = await session.scalar(select(Connector).where(Connector.id == connector_id, Connector.type == "webhook", Connector.status == "active"))
    expected = str(item.config.get("webhook_secret", "")) if item else ""
    if not expected or not hmac.compare_digest(x_webhook_secret, expected):
        raise HTTPException(401, "Invalid webhook secret")
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > 5 * 1024 * 1024:
            raise HTTPException(413, "Webhook payload exceeds 5 MB")
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise HTTPException(422, "Invalid JSON") from exc
    rows = payload if isinstance(payload, list) else [payload]
    if not rows or len(rows) > 5000 or any(not isinstance(row, dict) for row in rows):
        raise HTTPException(422, "Provide 1 to 5000 objects")
    mappings = await ConnectorRepository(session, item.tenant_id).mappings(item.id)
    try:
        result = await ShipmentService(session, item.tenant_id).import_rows(await WebhookConnector(rows).fetch_data(), mappings)
        background_tasks.add_task(analyze_new_exceptions, item.tenant_id, result.exception_ids)
        return result
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
