import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.tenant import Tenant
from app.models.user import User
from app.models.domain import Driver, LogisticsException, Route, Shipment, TrackingEvent, Vehicle
from app.rules.evaluator import RuleEvaluator


async def seed_development() -> None:
    settings = get_settings()
    async with SessionLocal() as session:
        tenant = await session.scalar(select(Tenant).where(Tenant.code == settings.dev_tenant_code))
        if tenant is None:
            tenant = Tenant(name=settings.dev_tenant_name, code=settings.dev_tenant_code)
            session.add(tenant)
            await session.flush()
        admin = await session.scalar(select(User).where(User.tenant_id == tenant.id, User.username == settings.dev_admin_username))
        if admin is None:
            session.add(User(tenant_id=tenant.id, username=settings.dev_admin_username, email=settings.dev_admin_email, password_hash=hash_password(settings.dev_admin_password), role="admin"))
        existing_demo = await session.scalar(select(Shipment.id).where(Shipment.tenant_id == tenant.id, Shipment.shipment_no == "DEMO000001"))
        if existing_demo is None:
            await seed_logistics(session, tenant.id)
        else:
            for item in (await session.scalars(select(LogisticsException).where(LogisticsException.tenant_id == tenant.id, LogisticsException.ai_analysis.is_(None)))).all():
                item.ai_analysis = f"规则分析：{item.reason}"
            cold_ids = [item.id for item in (await session.scalars(select(Shipment).where(Shipment.tenant_id == tenant.id))).all() if item.raw_data.get("cold_chain")]
            if cold_ids:
                for item in (await session.scalars(select(LogisticsException).where(LogisticsException.tenant_id == tenant.id, LogisticsException.shipment_id.in_(cold_ids)))).all():
                    if item.type == "ARRIVAL_DELAY":
                        item.level = "CRITICAL"
                    elif item.type == "TRACKING_STALE":
                        item.level = "HIGH"
        await session.commit()


async def seed_logistics(session: AsyncSession, tenant_id: str) -> None:
    now = datetime.now(timezone.utc)
    drivers = [Driver(tenant_id=tenant_id, external_id=f"DRV{i:03d}", name=f"演示司机{i}", raw_data={}) for i in range(1, 31)]
    vehicles = [Vehicle(tenant_id=tenant_id, external_id=f"VEH{i:03d}", plate_no=f"渝A{i:05d}", vehicle_type="冷链" if i % 10 == 0 else "厢式", raw_data={}) for i in range(1, 51)]
    destinations = ["秀山", "万州", "涪陵", "江津", "永川", "合川", "黔江", "南川", "长寿", "綦江"]
    routes = [Route(tenant_id=tenant_id, name=f"重庆→{name}", origin="重庆", destination=name) for name in destinations]
    session.add_all([*drivers, *vehicles, *routes])
    await session.flush()
    shipments: list[Shipment] = []
    for index in range(1, 1201):
        scenario = index % 8
        route = routes[index % len(routes)]
        base = now - timedelta(hours=index % 24, minutes=index % 60)
        is_delivered = scenario == 0
        status = "DELIVERED" if is_delivered else "ARRIVED" if scenario == 4 else "IN_TRANSIT"
        shipment = Shipment(
            tenant_id=tenant_id, shipment_no=f"DEMO{index:06d}", external_id=f"TMS-{index}", status=status,
            origin="重庆", destination=route.destination, sender_name=f"发货客户{index % 70 + 1}",
            receiver_name=f"收货客户{index % 130 + 1}",
            planned_departure_time=base - timedelta(hours=2),
            actual_departure_time=None if scenario == 1 else base - timedelta(hours=1, minutes=50),
            planned_arrival_time=base - timedelta(hours=1) if scenario == 2 else now + timedelta(hours=2),
            actual_arrival_time=now - timedelta(hours=3) if scenario == 4 else now - timedelta(minutes=20) if is_delivered else None,
            signed_at=now - timedelta(minutes=15) if is_delivered else None,
            latest_tracking_time=now - timedelta(hours=6) if scenario == 3 else now - timedelta(minutes=30),
            driver_id=None if scenario == 5 else drivers[index % len(drivers)].id,
            vehicle_id=None if scenario == 6 else vehicles[index % len(vehicles)].id,
            route_id=route.id,
            raw_data={"source": "development-seed", "source_id": f"TMS-{index}", "cold_chain": index % 10 == 0},
        )
        shipments.append(shipment)
    session.add_all(shipments)
    await session.flush()
    events: list[TrackingEvent] = []
    exceptions: list[LogisticsException] = []
    evaluator = RuleEvaluator()
    for index, shipment in enumerate(shipments, start=1):
        for step in range(5):
            event_time = shipment.latest_tracking_time - timedelta(minutes=(4 - step) * 40)
            events.append(TrackingEvent(tenant_id=tenant_id, shipment_id=shipment.id, event_type="LOCATION",
                location="重庆" if step < 3 else shipment.destination, event_time=event_time,
                raw_data={"step": step, "source": "development-seed"}))
        for result in evaluator.evaluate(shipment, now):
            exceptions.append(LogisticsException(tenant_id=tenant_id, shipment_id=shipment.id, type=result.code,
                level=result.level, status="open", rule_code=result.code, reason=result.reason,
                ai_analysis=f"规则分析：{result.reason}", suggestion=result.suggestion, detected_at=now))
    session.add_all([*events, *exceptions])


if __name__ == "__main__":
    asyncio.run(seed_development())
