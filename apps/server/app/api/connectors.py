from typing import Annotated

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.connectors.file import FileConnector, MAX_UPLOAD_BYTES
from app.db.session import get_session
from app.schemas.connector import ConnectorInput, ConnectorOutput, ImportResult, MappingOutput, MappingReplace
from app.services.auth import AuthenticatedUser
from app.services.connector import ConnectorService, connector_output
from app.services.shipments import ShipmentService
from app.tasks.exception_analysis import analyze_new_exceptions

router = APIRouter(prefix="/api/v1/connectors", tags=["connectors"])


def service(session: AsyncSession, current: AuthenticatedUser) -> ConnectorService:
    return ConnectorService(session, current.user.tenant_id)


async def required_connector(svc: ConnectorService, connector_id: str):
    item = await svc.repo.get(connector_id)
    if item is None:
        raise HTTPException(404, "Connector not found")
    return item


@router.get("", response_model=list[ConnectorOutput])
async def list_connectors(session: Annotated[AsyncSession, Depends(get_session)], current: Annotated[AuthenticatedUser, Depends(get_current_user)]):
    return [connector_output(item) for item in await service(session, current).repo.list()]


@router.post("", response_model=ConnectorOutput, status_code=201)
async def create_connector(payload: ConnectorInput, session: Annotated[AsyncSession, Depends(get_session)], current: Annotated[AuthenticatedUser, Depends(get_current_user)]):
    try:
        item = await service(session, current).create(payload)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return connector_output(item)


@router.get("/{connector_id}", response_model=ConnectorOutput)
async def get_connector(connector_id: str, session: Annotated[AsyncSession, Depends(get_session)], current: Annotated[AuthenticatedUser, Depends(get_current_user)]):
    return connector_output(await required_connector(service(session, current), connector_id))


@router.put("/{connector_id}", response_model=ConnectorOutput)
async def update_connector(connector_id: str, payload: ConnectorInput, session: Annotated[AsyncSession, Depends(get_session)], current: Annotated[AuthenticatedUser, Depends(get_current_user)]):
    svc = service(session, current)
    item = await required_connector(svc, connector_id)
    try:
        return connector_output(await svc.update(item, payload))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.delete("/{connector_id}", status_code=204)
async def delete_connector(connector_id: str, session: Annotated[AsyncSession, Depends(get_session)], current: Annotated[AuthenticatedUser, Depends(get_current_user)]):
    svc = service(session, current)
    await svc.delete(await required_connector(svc, connector_id))


@router.post("/{connector_id}/test")
async def test_connector(connector_id: str, session: Annotated[AsyncSession, Depends(get_session)], current: Annotated[AuthenticatedUser, Depends(get_current_user)]):
    svc = service(session, current)
    item = await required_connector(svc, connector_id)
    try:
        await svc.fetch(item, sample=True)
    except (ValueError, httpx.HTTPError) as exc:
        raise HTTPException(502, f"Connection test failed: {type(exc).__name__}") from exc
    return {"ok": True}


@router.post("/{connector_id}/sample")
async def sample_connector(connector_id: str, session: Annotated[AsyncSession, Depends(get_session)], current: Annotated[AuthenticatedUser, Depends(get_current_user)]):
    svc = service(session, current)
    item = await required_connector(svc, connector_id)
    try:
        rows = await svc.fetch(item, sample=True)
    except (ValueError, httpx.HTTPError) as exc:
        raise HTTPException(502, f"Sample fetch failed: {type(exc).__name__}") from exc
    return {"fields": list(rows[0].keys()) if rows else [], "rows": rows}


@router.get("/{connector_id}/mappings", response_model=list[MappingOutput])
async def list_mappings(connector_id: str, session: Annotated[AsyncSession, Depends(get_session)], current: Annotated[AuthenticatedUser, Depends(get_current_user)]):
    svc = service(session, current)
    await required_connector(svc, connector_id)
    return [MappingOutput(id=item.id, connector_id=item.connector_id, entity_type=item.entity_type,
        source_field=item.source_field, target_field=item.target_field, transform=item.transform,
        required=item.required) for item in await svc.repo.mappings(connector_id)]


@router.put("/{connector_id}/mappings", response_model=list[MappingOutput])
@router.post("/{connector_id}/mappings", response_model=list[MappingOutput])
async def replace_mappings(connector_id: str, payload: MappingReplace, session: Annotated[AsyncSession, Depends(get_session)], current: Annotated[AuthenticatedUser, Depends(get_current_user)]):
    try:
        items = await service(session, current).replace_mappings(connector_id, payload.mappings)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return [MappingOutput(id=item.id, connector_id=item.connector_id, entity_type=item.entity_type,
        source_field=item.source_field, target_field=item.target_field, transform=item.transform,
        required=item.required) for item in items]


@router.post("/{connector_id}/sync", response_model=ImportResult)
async def sync_connector(connector_id: str, background_tasks: BackgroundTasks, session: Annotated[AsyncSession, Depends(get_session)], current: Annotated[AuthenticatedUser, Depends(get_current_user)]):
    svc = service(session, current)
    item = await required_connector(svc, connector_id)
    try:
        rows = await svc.fetch(item)
        result = await ShipmentService(session, current.user.tenant_id).import_rows(rows, await svc.repo.mappings(connector_id))
        background_tasks.add_task(analyze_new_exceptions, current.user.tenant_id, result.exception_ids)
        return result
    except (ValueError, httpx.HTTPError) as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/{connector_id}/upload", response_model=ImportResult)
async def upload_connector(connector_id: str, background_tasks: BackgroundTasks, session: Annotated[AsyncSession, Depends(get_session)], current: Annotated[AuthenticatedUser, Depends(get_current_user)], file: UploadFile = File(...)):
    svc = service(session, current)
    item = await required_connector(svc, connector_id)
    if item.type != "file":
        raise HTTPException(422, "Connector is not a file connector")
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    try:
        rows = await FileConnector(file.filename or "", data).fetch_data()
        result = await ShipmentService(session, current.user.tenant_id).import_rows(rows, await svc.repo.mappings(connector_id))
        background_tasks.add_task(analyze_new_exceptions, current.user.tenant_id, result.exception_ids)
        return result
    except (ValueError, UnicodeError) as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(422, "File could not be parsed") from exc


@router.post("/{connector_id}/file-sample")
async def file_sample(connector_id: str, session: Annotated[AsyncSession, Depends(get_session)], current: Annotated[AuthenticatedUser, Depends(get_current_user)], file: UploadFile = File(...)):
    svc = service(session, current)
    item = await required_connector(svc, connector_id)
    if item.type != "file":
        raise HTTPException(422, "Connector is not a file connector")
    try:
        rows = await FileConnector(file.filename or "", await file.read(MAX_UPLOAD_BYTES + 1)).fetch_sample()
    except (ValueError, UnicodeError) as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(422, "File could not be parsed") from exc
    return {"fields": list(rows[0]), "rows": rows[:5]}


@router.post("/{connector_id}/import", response_model=ImportResult)
async def import_json(connector_id: str, rows: list[dict], background_tasks: BackgroundTasks, session: Annotated[AsyncSession, Depends(get_session)], current: Annotated[AuthenticatedUser, Depends(get_current_user)]):
    if not rows or len(rows) > 5000:
        raise HTTPException(422, "Provide 1 to 5000 records")
    svc = service(session, current)
    await required_connector(svc, connector_id)
    try:
        result = await ShipmentService(session, current.user.tenant_id).import_rows(rows, await svc.repo.mappings(connector_id))
        background_tasks.add_task(analyze_new_exceptions, current.user.tenant_id, result.exception_ids)
        return result
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
