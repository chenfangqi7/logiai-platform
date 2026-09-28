from typing import Annotated

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.deps import get_current_user
from app.connectors.file import FileConnector, MAX_UPLOAD_BYTES
from app.db.session import get_session
from app.models.domain import FieldMapping
from app.schemas.connector import ConnectorInput, ConnectorOutput, ImportResult, MappingOutput, MappingPreviewInput, MappingReplace, SyncIssueOutput, SyncJobOutput, TrackingMappingInput, TrackingMappingOutput
from app.services.auth import AuthenticatedUser
from app.services.connector import ConnectorService, connector_output
from app.services.mapping import STATUSES, ShipmentImportData, describe_sample_fields, preview_shipment, suggest_mappings
from app.services.shipments import ShipmentService
from app.services.sync_jobs import SyncJobService, run_sync_job
from app.tasks.exception_analysis import analyze_new_exceptions

router = APIRouter(prefix="/api/v1/connectors", tags=["connectors"])
mapping_router = APIRouter(prefix="/api/v1/mapping", tags=["mapping"])


@mapping_router.get("/fields/shipment")
async def shipment_mapping_fields(current: Annotated[AuthenticatedUser, Depends(get_current_user)]):
    labels = {
        "shipment_no": "运单号", "external_id": "外部编号", "status": "状态", "origin": "始发地",
        "destination": "目的地", "sender_name": "发货人", "receiver_name": "收货人",
        "driver_external_id": "司机编号", "vehicle_plate_no": "车牌号", "route_name": "线路名称",
    }
    return [{"name": name, "label": labels.get(name, name),
             "type": "enum" if name == "status" else "datetime" if "time" in name or name == "signed_at" else "string",
             "options": sorted(STATUSES) if name == "status" else [],
             "required": name == "shipment_no"} for name in ShipmentImportData.model_fields]


@mapping_router.post("/suggestions")
async def mapping_suggestions(fields: list[str], current: Annotated[AuthenticatedUser, Depends(get_current_user)]):
    return suggest_mappings(fields[:200])


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
        return await svc.test(item)
    except (ValueError, httpx.HTTPError) as exc:
        raise HTTPException(502, f"Connection test failed: {type(exc).__name__}") from exc


@router.post("/{connector_id}/sample")
async def sample_connector(connector_id: str, session: Annotated[AsyncSession, Depends(get_session)], current: Annotated[AuthenticatedUser, Depends(get_current_user)]):
    svc = service(session, current)
    item = await required_connector(svc, connector_id)
    try:
        rows = await svc.fetch(item, sample=True)
    except (ValueError, httpx.HTTPError) as exc:
        raise HTTPException(502, f"Sample fetch failed: {type(exc).__name__}") from exc
    details = describe_sample_fields(rows)
    return {"fields": [item["path"] for item in details], "field_details": details, "rows": rows}


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


@router.post("/{connector_id}/mapping/preview")
async def preview_mapping(connector_id: str, payload: MappingPreviewInput, session: Annotated[AsyncSession, Depends(get_session)], current: Annotated[AuthenticatedUser, Depends(get_current_user)]):
    svc = service(session, current)
    await required_connector(svc, connector_id)
    try:
        svc.validate_mappings(payload.mappings)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    mappings = [FieldMapping(tenant_id=current.user.tenant_id, connector_id=connector_id, entity_type="shipment", **item.model_dump()) for item in payload.mappings]
    return preview_shipment(payload.sample, mappings)


@router.get("/{connector_id}/tracking-mapping", response_model=TrackingMappingOutput | None)
async def get_tracking_mapping(connector_id: str, session: Annotated[AsyncSession, Depends(get_session)], current: Annotated[AuthenticatedUser, Depends(get_current_user)]):
    svc = service(session, current)
    await required_connector(svc, connector_id)
    return await svc.repo.tracking_mapping(connector_id)


@router.put("/{connector_id}/tracking-mapping", response_model=TrackingMappingOutput)
async def put_tracking_mapping(connector_id: str, payload: TrackingMappingInput, session: Annotated[AsyncSession, Depends(get_session)], current: Annotated[AuthenticatedUser, Depends(get_current_user)]):
    try:
        return await service(session, current).replace_tracking_mapping(connector_id, payload)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/{connector_id}/sync", response_model=ImportResult)
async def sync_connector(connector_id: str, background_tasks: BackgroundTasks, session: Annotated[AsyncSession, Depends(get_session)], current: Annotated[AuthenticatedUser, Depends(get_current_user)]):
    await required_connector(service(session, current), connector_id)
    try:
        job = await SyncJobService(session, current.user.tenant_id).create(connector_id)
        await run_sync_job(job.id, connector_id, current.user.tenant_id, async_sessionmaker(session.bind, expire_on_commit=False))
        await session.refresh(job)
        if job.status == "FAILED" and not job.result:
            raise HTTPException(422, job.error_message or "Sync failed")
        result = ImportResult.model_validate(job.result)
        background_tasks.add_task(analyze_new_exceptions, current.user.tenant_id, result.exception_ids)
        return result
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/{connector_id}/sync-jobs", response_model=SyncJobOutput, status_code=202)
async def start_sync_job(connector_id: str, background_tasks: BackgroundTasks, session: Annotated[AsyncSession, Depends(get_session)], current: Annotated[AuthenticatedUser, Depends(get_current_user)]):
    try:
        job = await SyncJobService(session, current.user.tenant_id).create(connector_id)
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    background_tasks.add_task(run_sync_job, job.id, connector_id, current.user.tenant_id,
        async_sessionmaker(session.bind, expire_on_commit=False))
    return job


@router.get("/{connector_id}/sync-jobs", response_model=list[SyncJobOutput])
async def list_sync_jobs(connector_id: str, session: Annotated[AsyncSession, Depends(get_session)], current: Annotated[AuthenticatedUser, Depends(get_current_user)]):
    svc = service(session, current)
    await required_connector(svc, connector_id)
    return await SyncJobService(session, current.user.tenant_id).list(connector_id)


@router.get("/{connector_id}/sync-jobs/{job_id}", response_model=SyncJobOutput)
async def get_sync_job(connector_id: str, job_id: str, session: Annotated[AsyncSession, Depends(get_session)], current: Annotated[AuthenticatedUser, Depends(get_current_user)]):
    await required_connector(service(session, current), connector_id)
    job = await SyncJobService(session, current.user.tenant_id).get(connector_id, job_id)
    if job is None:
        raise HTTPException(404, "Sync job not found")
    return job


@router.get("/{connector_id}/sync-jobs/{job_id}/issues", response_model=list[SyncIssueOutput])
async def list_sync_issues(connector_id: str, job_id: str, session: Annotated[AsyncSession, Depends(get_session)], current: Annotated[AuthenticatedUser, Depends(get_current_user)]):
    await required_connector(service(session, current), connector_id)
    issues = await SyncJobService(session, current.user.tenant_id).issues(connector_id, job_id)
    if issues is None:
        raise HTTPException(404, "Sync job not found")
    return issues


@router.post("/{connector_id}/upload", response_model=ImportResult)
async def upload_connector(connector_id: str, background_tasks: BackgroundTasks, session: Annotated[AsyncSession, Depends(get_session)], current: Annotated[AuthenticatedUser, Depends(get_current_user)], file: UploadFile = File(...)):
    svc = service(session, current)
    item = await required_connector(svc, connector_id)
    if item.type != "file":
        raise HTTPException(422, "Connector is not a file connector")
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    try:
        rows = await FileConnector(file.filename or "", data).fetch_data()
        result = await ShipmentService(session, current.user.tenant_id).import_rows(rows, await svc.repo.mappings(connector_id), connector_id, await svc.repo.tracking_mapping(connector_id))
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
    details = describe_sample_fields(rows)
    return {"fields": [item["path"] for item in details], "field_details": details, "rows": rows[:5]}


@router.post("/{connector_id}/import", response_model=ImportResult)
async def import_json(connector_id: str, rows: list[dict], background_tasks: BackgroundTasks, session: Annotated[AsyncSession, Depends(get_session)], current: Annotated[AuthenticatedUser, Depends(get_current_user)]):
    if not rows or len(rows) > 5000:
        raise HTTPException(422, "Provide 1 to 5000 records")
    svc = service(session, current)
    await required_connector(svc, connector_id)
    try:
        result = await ShipmentService(session, current.user.tenant_id).import_rows(rows, await svc.repo.mappings(connector_id), connector_id, await svc.repo.tracking_mapping(connector_id))
        background_tasks.add_task(analyze_new_exceptions, current.user.tenant_id, result.exception_ids)
        return result
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
