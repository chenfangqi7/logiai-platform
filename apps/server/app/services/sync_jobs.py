from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.domain import SyncIssue, SyncJob
from app.rules.evaluator import aware
from app.repositories.connector import ConnectorRepository
from app.services.connector import ConnectorService
from app.services.shipments import ShipmentService


class SyncJobService:
    def __init__(self, session: AsyncSession, tenant_id: str) -> None:
        self.session = session
        self.tenant_id = tenant_id

    async def create(self, connector_id: str) -> SyncJob:
        connector = await ConnectorRepository(self.session, self.tenant_id).get(connector_id)
        if connector is None:
            raise ValueError("Connector not found")
        if connector.type != "rest" or connector.status != "active":
            raise ValueError("Only active REST connectors support sync jobs")
        mappings = await ConnectorRepository(self.session, self.tenant_id).mappings(connector_id)
        if not mappings:
            raise ValueError("Configure field mappings before syncing")
        active = await self.session.scalar(select(SyncJob).where(SyncJob.tenant_id == self.tenant_id,
            SyncJob.connector_id == connector_id, SyncJob.status.in_(["PENDING", "RUNNING"])))
        if active:
            started = active.started_at or active.created_at
            if started and datetime.now(timezone.utc) - aware(started) > timedelta(hours=1):
                active.status = "FAILED"
                active.finished_at = datetime.now(timezone.utc)
                active.error_message = "Worker interrupted before completion"
                await self.session.commit()
            else:
                raise RuntimeError("A sync job is already running for this connector")
        job = SyncJob(tenant_id=self.tenant_id, connector_id=connector_id, status="PENDING", result={})
        self.session.add(job)
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise RuntimeError("A sync job is already running for this connector") from exc
        await self.session.refresh(job)
        return job

    async def get(self, connector_id: str, job_id: str) -> SyncJob | None:
        return await self.session.scalar(select(SyncJob).where(SyncJob.tenant_id == self.tenant_id,
            SyncJob.connector_id == connector_id, SyncJob.id == job_id))

    async def list(self, connector_id: str, limit: int = 20) -> list[SyncJob]:
        return list((await self.session.scalars(select(SyncJob).where(SyncJob.tenant_id == self.tenant_id,
            SyncJob.connector_id == connector_id).order_by(SyncJob.created_at.desc()).limit(limit))).all())

    async def issues(self, connector_id: str, job_id: str) -> list[SyncIssue] | None:
        if await self.get(connector_id, job_id) is None:
            return None
        return list((await self.session.scalars(select(SyncIssue).where(SyncIssue.tenant_id == self.tenant_id,
            SyncIssue.connector_id == connector_id, SyncIssue.job_id == job_id).order_by(SyncIssue.created_at, SyncIssue.row_number))).all())


async def run_sync_job(job_id: str, connector_id: str, tenant_id: str, session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with session_factory() as session:
        service = SyncJobService(session, tenant_id)
        job = await service.get(connector_id, job_id)
        if job is None or job.status != "PENDING":
            return
        job.status = "RUNNING"
        job.started_at = datetime.now(timezone.utc)
        await session.commit()
        try:
            connector_service = ConnectorService(session, tenant_id)
            connector = await connector_service.repo.get(connector_id)
            if connector is None:
                raise ValueError("Connector no longer exists")
            rows = await connector_service.fetch(connector)
            mappings = await connector_service.repo.mappings(connector_id)
            incremental_field = connector.config.get("incremental_field") if connector.config.get("sync_mode") == "INCREMENTAL" else None
            result = await ShipmentService(session, tenant_id).import_rows(rows, mappings, connector_id,
                await connector_service.repo.tracking_mapping(connector_id), incremental_field)
            if result.checkpoint:
                connector.config = {**connector.config, "last_sync_value": result.checkpoint}
            job.status = "PARTIAL_SUCCESS" if result.failed and result.success else "FAILED" if result.failed else "SUCCESS"
            job.total_count = result.total
            job.success_count = result.success
            job.failed_count = result.failed
            job.result = result.model_dump()
            session.add_all([SyncIssue(tenant_id=tenant_id, connector_id=connector_id, job_id=job_id,
                row_number=issue["row_number"], entity=issue["entity"], external_id=None,
                level=issue["level"], code=issue["code"], message=issue["message"])
                for issue in result.issues])
        except (ValueError, httpx.HTTPError) as exc:
            await session.rollback()
            job = await service.get(connector_id, job_id)
            if job is None:
                return
            job.status = "FAILED"
            job.error_message = str(exc) if str(exc) in {"Connector no longer exists", "Configure field mappings before importing"} else type(exc).__name__
            session.add(SyncIssue(tenant_id=tenant_id, connector_id=connector_id, job_id=job_id,
                row_number=None, entity="connector", external_id=None, level="FATAL", code="SYNC_FAILED", message=job.error_message))
        except Exception as exc:
            await session.rollback()
            job = await service.get(connector_id, job_id)
            if job is None:
                return
            job.status = "FAILED"
            job.error_message = type(exc).__name__
            session.add(SyncIssue(tenant_id=tenant_id, connector_id=connector_id, job_id=job_id,
                row_number=None, entity="connector", external_id=None, level="FATAL", code="SYNC_FAILED", message=job.error_message))
        job.finished_at = datetime.now(timezone.utc)
        await session.commit()
