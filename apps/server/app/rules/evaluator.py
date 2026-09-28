from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.models.domain import Shipment


def aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


@dataclass(frozen=True)
class RuleResult:
    code: str
    level: str
    reason: str
    suggestion: str


class RuleEvaluator:
    def evaluate(self, shipment: Shipment, now: datetime | None = None) -> list[RuleResult]:
        now = now or datetime.now(timezone.utc)
        results: list[RuleResult] = []
        departure = aware(shipment.planned_departure_time)
        arrival = aware(shipment.planned_arrival_time)
        latest = aware(shipment.latest_tracking_time)
        actual_arrival = aware(shipment.actual_arrival_time)
        cold_chain = bool((shipment.raw_data or {}).get("cold_chain"))

        if departure and not shipment.actual_departure_time and shipment.status not in {"DELIVERED", "CANCELLED"} and now > departure + timedelta(minutes=30):
            results.append(RuleResult("DEPARTURE_DELAY", "HIGH", "计划发车时间已超过 30 分钟，尚无实际发车记录。", "联系承运方确认车辆和司机状态，更新预计发车时间。"))
        if arrival and shipment.status not in {"DELIVERED", "CANCELLED"} and now > arrival:
            results.append(RuleResult("ARRIVAL_DELAY", "CRITICAL" if cold_chain else "HIGH", "已超过计划到达时间，运单尚未妥投。", "核实当前位置和预计到达时间，必要时通知客户。"))
        if shipment.status in {"PICKED_UP", "IN_TRANSIT", "DELIVERING"} and latest and now - latest > timedelta(hours=4):
            results.append(RuleResult("TRACKING_STALE", "HIGH" if cold_chain else "MEDIUM", "轨迹超过 4 小时未更新。", "联系司机或定位服务确认实际位置。"))
        if shipment.status in {"ARRIVED", "DELIVERING"} and actual_arrival and not shipment.signed_at and now - actual_arrival > timedelta(hours=2):
            results.append(RuleResult("UNSIGNED_TOO_LONG", "MEDIUM", "到达后超过 2 小时仍未签收。", "联系收货方核实签收障碍并记录处理结果。"))
        missing = [name for name, value in {
            "司机": shipment.driver_id, "车辆": shipment.vehicle_id, "起点": shipment.origin,
            "终点": shipment.destination, "计划到达时间": shipment.planned_arrival_time,
        }.items() if not value]
        if missing:
            results.append(RuleResult("DATA_MISSING", "LOW", f"缺少必要字段：{'、'.join(missing)}。", "从源系统补全字段映射或补录数据。"))
        return results
