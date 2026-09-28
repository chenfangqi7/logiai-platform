from datetime import datetime
from uuid import uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

JsonType = JSON().with_variant(JSONB(), "postgresql")
EmbeddingType = Vector(1536).with_variant(JSON(), "sqlite")


class Identity:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()), comment="记录唯一主键UUID")
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False, index=True, comment="所属租户ID")


class Timestamped:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="记录创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="最后更新时间")


class Connector(Identity, Timestamped, Base):
    __tablename__ = "connectors"
    __table_args__ = {"comment": "数据连接器配置表"}
    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="连接器名称")
    type: Mapped[str] = mapped_column(String(20), nullable=False, comment="连接器类型(rest=API接口, database=数据库, file=文件导入, webhook=回调接收)")
    base_url: Mapped[str | None] = mapped_column(String(2048), comment="服务接入基础URL地址")
    auth_type: Mapped[str] = mapped_column(String(30), nullable=False, default="none", comment="认证方式(none=无, basic=BasicAuth, bearer=BearerToken, api_key=API密钥)")
    config: Mapped[dict] = mapped_column(JsonType, nullable=False, default=dict, comment="连接器详细配置与凭证参数(加密存储)")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", comment="连接器状态(active=启用, inactive=停用, error=异常)")


class FieldMapping(Identity, Timestamped, Base):
    __tablename__ = "field_mappings"
    __table_args__ = (
        UniqueConstraint("tenant_id", "connector_id", "entity_type", "source_field", name="uq_mapping_source"),
        {"comment": "数据字段映射规则表"},
    )
    connector_id: Mapped[str] = mapped_column(String(36), ForeignKey("connectors.id"), nullable=False, index=True, comment="关联连接器ID")
    entity_type: Mapped[str] = mapped_column(String(30), nullable=False, default="shipment", comment="目标实体对象类型(shipment=运单, event=轨迹事件, vehicle=车辆, driver=司机)")
    source_field: Mapped[str] = mapped_column(String(200), nullable=False, comment="外部源数据字段路径")
    target_field: Mapped[str] = mapped_column(String(100), nullable=False, comment="系统标准模型目标字段名")
    transform: Mapped[dict] = mapped_column(JsonType, nullable=False, default=dict, comment="字段转换规则配置(日期解析、枚举映射、默认值等)")
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="是否为必填关键字段")


class CollectionMapping(Identity, Timestamped, Base):
    __tablename__ = "collection_mappings"
    __table_args__ = (
        UniqueConstraint("tenant_id", "connector_id", "target_entity", name="uq_collection_mapping_entity"),
        {"comment": "集合嵌套对象映射配置表"},
    )
    connector_id: Mapped[str] = mapped_column(String(36), ForeignKey("connectors.id"), nullable=False, index=True, comment="关联连接器ID")
    source_field: Mapped[str] = mapped_column(String(200), nullable=False, comment="外部源数据中嵌套数组集合字段名(如events)")
    target_entity: Mapped[str] = mapped_column(String(40), nullable=False, comment="映射的目标集合实体名(如tracking_events)")
    fields: Mapped[list] = mapped_column(JsonType, nullable=False, default=list, comment="集合内部子字段映射规则列表")


class SyncJob(Identity, Base):
    __tablename__ = "sync_jobs"
    __table_args__ = (
        Index("uq_sync_jobs_active_connector", "tenant_id", "connector_id", unique=True,
              postgresql_where=text("status IN ('PENDING', 'RUNNING')"),
              sqlite_where=text("status IN ('PENDING', 'RUNNING')")),
        {"comment": "数据同步任务记录表"},
    )
    connector_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True, comment="关联连接器ID")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING", comment="任务执行状态(PENDING=待运行, RUNNING=执行中, SUCCESS=成功, FAILED=失败, PARTIAL=部分成功)")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="任务开始执行时间")
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="任务结束完成时间")
    total_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="本次待同步总数据条数")
    success_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="成功同步写入数据条数")
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="失败或校验未通过数据条数")
    result: Mapped[dict] = mapped_column(JsonType, nullable=False, default=dict, comment="任务执行统计与处理结果摘要")
    error_message: Mapped[str | None] = mapped_column(String(500), comment="执行失败时的错误摘要信息")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="任务创建时间")


class SyncIssue(Identity, Base):
    __tablename__ = "sync_issues"
    __table_args__ = {"comment": "数据同步问题与校验异常明细表"}
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("sync_jobs.id"), nullable=False, index=True, comment="关联同步任务ID")
    connector_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True, comment="关联连接器ID")
    row_number: Mapped[int | None] = mapped_column(Integer, comment="原始数据行号或记录序号")
    entity: Mapped[str] = mapped_column(String(40), nullable=False, comment="异常发生的目标实体类型")
    external_id: Mapped[str | None] = mapped_column(String(100), comment="外部源数据原始单号或业务主键")
    level: Mapped[str] = mapped_column(String(10), nullable=False, comment="问题严重级别(WARNING=警告, ERROR=错误)")
    code: Mapped[str] = mapped_column(String(60), nullable=False, comment="异常错误分类编码")
    message: Mapped[str] = mapped_column(String(500), nullable=False, comment="详细错误原因说明")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="记录创建时间")


class Vehicle(Identity, Timestamped, Base):
    __tablename__ = "vehicles"
    __table_args__ = (
        UniqueConstraint("tenant_id", "plate_no", name="uq_vehicle_plate"),
        {"comment": "运力车辆信息表"},
    )
    external_id: Mapped[str | None] = mapped_column(String(100), comment="外部系统车辆原始业务主键")
    plate_no: Mapped[str] = mapped_column(String(30), nullable=False, comment="车辆牌照号码")
    vehicle_type: Mapped[str | None] = mapped_column(String(60), comment="车型分类(如4.2米箱货、9.6米高栏、17.5米平板)")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active", comment="车辆运营状态(active=运营中, maintenance=维修中, retired=已停用)")
    raw_data: Mapped[dict] = mapped_column(JsonType, nullable=False, default=dict, comment="外部原始数据快照")


class Driver(Identity, Timestamped, Base):
    __tablename__ = "drivers"
    __table_args__ = {"comment": "司机运力人员信息表"}
    external_id: Mapped[str | None] = mapped_column(String(100), comment="外部系统司机原始业务主键")
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="司机姓名")
    phone: Mapped[str | None] = mapped_column(String(40), comment="司机联系手机号码")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active", comment="司机工作状态(active=在职接单, resting=休息中, inactive=已离职)")
    raw_data: Mapped[dict] = mapped_column(JsonType, nullable=False, default=dict, comment="外部原始数据快照")


class Route(Identity, Timestamped, Base):
    __tablename__ = "routes"
    __table_args__ = {"comment": "运输线路规划信息表"}
    name: Mapped[str] = mapped_column(String(160), nullable=False, comment="线路名称(如华东干线-沪京线)")
    origin: Mapped[str] = mapped_column(String(200), nullable=False, comment="起点城市/始发枢纽仓")
    destination: Mapped[str] = mapped_column(String(200), nullable=False, comment="终点城市/目的配送中心")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active", comment="线路启用状态(active=有效运营, inactive=暂停运营)")


class Shipment(Identity, Timestamped, Base):
    __tablename__ = "shipments"
    __table_args__ = (
        UniqueConstraint("tenant_id", "shipment_no", name="uq_shipment_no"),
        Index("uq_shipments_tenant_source", "tenant_id", "source_connector_id", "source_external_id", unique=True,
              postgresql_where=text("source_connector_id IS NOT NULL AND source_external_id IS NOT NULL"),
              sqlite_where=text("source_connector_id IS NOT NULL AND source_external_id IS NOT NULL")),
        {"comment": "物流运单业务主表"},
    )
    shipment_no: Mapped[str] = mapped_column(String(100), nullable=False, index=True, comment="系统标准运单唯一跟踪编号")
    external_id: Mapped[str | None] = mapped_column(String(100), comment="外部TMS/ERP系统原始运单编号")
    source_connector_id: Mapped[str | None] = mapped_column(String(36), index=True, comment="接入来源连接器ID")
    source_external_id: Mapped[str | None] = mapped_column(String(100), comment="外部源系统的全局唯一业务记录主键")
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="外部系统源数据最新更新时间")
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="本系统最近一次成功同步写入时间")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="UNKNOWN", comment="运单当前生命周期状态(CREATED=已创建, DISPATCHED=已调度, IN_TRANSIT=运输中, ARRIVED=已到达, DELIVERED=已签收, EXCEPTION=异常阻断, CANCELLED=已取消)")
    origin: Mapped[str | None] = mapped_column(String(200), comment="始发地点或发货网点")
    destination: Mapped[str | None] = mapped_column(String(200), comment="目的地点或收货网点")
    sender_name: Mapped[str | None] = mapped_column(String(100), comment="发货人或发货单位名称")
    receiver_name: Mapped[str | None] = mapped_column(String(100), comment="收货人或收货单位名称")
    planned_departure_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="计划发货启运时间")
    actual_departure_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="实际发车出库时间")
    planned_arrival_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="预计到达签收时间")
    actual_arrival_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="实际运抵终点时间")
    latest_tracking_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="最新物流轨迹上报时间")
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="收货人确认签收时间")
    driver_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("drivers.id"), comment="承运关联司机ID")
    vehicle_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("vehicles.id"), comment="承运关联车辆ID")
    route_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("routes.id"), comment="规划运输线路ID")
    raw_data: Mapped[dict] = mapped_column(JsonType, nullable=False, default=dict, comment="外部原始业务报文JSON快照")


class TrackingEvent(Identity, Base):
    __tablename__ = "tracking_events"
    __table_args__ = (
        Index("uq_tracking_source_event", "tenant_id", "shipment_id", "external_event_id", unique=True,
              postgresql_where=text("external_event_id IS NOT NULL"), sqlite_where=text("external_event_id IS NOT NULL")),
        {"comment": "运单物流轨迹事件流水表"},
    )
    shipment_id: Mapped[str] = mapped_column(String(36), ForeignKey("shipments.id"), nullable=False, index=True, comment="关联运单ID")
    event_type: Mapped[str] = mapped_column(String(60), nullable=False, comment="轨迹事件类型(DEPARTURE=发车, CHECKPOINT=途径打卡, TRANSIT=在途中, ARRIVAL=到达, DELIVERY=派送签收)")
    external_event_id: Mapped[str | None] = mapped_column(String(100), comment="外部系统原始轨迹事件唯一流水号")
    location: Mapped[str | None] = mapped_column(String(200), comment="轨迹发生地点描述")
    longitude: Mapped[float | None] = mapped_column(Float, comment="地理位置经度坐标")
    latitude: Mapped[float | None] = mapped_column(Float, comment="地理位置纬度坐标")
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, comment="轨迹事件发生的业务时间")
    raw_data: Mapped[dict] = mapped_column(JsonType, nullable=False, default=dict, comment="轨迹原始上报节点数据")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="数据写入系统时间")


class LogisticsException(Identity, Timestamped, Base):
    __tablename__ = "exceptions"
    __table_args__ = (
        UniqueConstraint("tenant_id", "shipment_id", "rule_code", name="uq_exception_rule"),
        {"comment": "物流异常事件及研判处置表"},
    )
    shipment_id: Mapped[str] = mapped_column(String(36), ForeignKey("shipments.id"), nullable=False, index=True, comment="关联运单ID")
    type: Mapped[str] = mapped_column(String(40), nullable=False, comment="异常分类(DELAY=时效延误, ROUTE_DEVIATION=路线偏离, TEMPERATURE_OUT_OF_RANGE=温控越界, DAMAGE=货损货差, OVERDUE=超期未交付)")
    level: Mapped[str] = mapped_column(String(20), nullable=False, comment="异常严重级别(LOW=轻微, MEDIUM=中度, HIGH=高危, CRITICAL=紧急告警)")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open", comment="异常处理处置状态(open=待处理, in_progress=跟进中, resolved=已解决, closed=已结案忽略)")
    rule_code: Mapped[str] = mapped_column(String(50), nullable=False, comment="触发此异常的规则策略代码")
    reason: Mapped[str] = mapped_column(Text, nullable=False, comment="系统判定的异常成因描述")
    ai_analysis: Mapped[str | None] = mapped_column(Text, comment="AI大模型智能研判与根因诊断分析")
    suggestion: Mapped[str | None] = mapped_column(Text, comment="AI大模型或规则引擎推荐的应对处置方案")
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, comment="系统初次检测发现异常的时间")
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="异常处置完毕闭环时间")


class AIConversation(Identity, Timestamped, Base):
    __tablename__ = "ai_conversations"
    __table_args__ = {"comment": "AI助手会话主题表"}
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, comment="发起会话的用户ID")
    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="会话主题标题")


class AIMessage(Identity, Base):
    __tablename__ = "ai_messages"
    __table_args__ = {"comment": "AI助手对话消息明细表"}
    conversation_id: Mapped[str] = mapped_column(String(36), ForeignKey("ai_conversations.id"), nullable=False, index=True, comment="所属对话会话ID")
    role: Mapped[str] = mapped_column(String(20), nullable=False, comment="消息发送角色(user=用户, assistant=AI模型, system=系统预置)")
    content: Mapped[Text] = mapped_column(Text, nullable=False, comment="消息正文内容")
    provider: Mapped[str | None] = mapped_column(String(50), comment="模型调用网关或提供方名称")
    model: Mapped[str | None] = mapped_column(String(100), comment="实际执行推理的大模型名称")
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="本次调用输入的Prompt Token数")
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="本次调用输出的Completion Token数")
    cost: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False, default=0, comment="本次调用预估计费成本(人民币元)")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="消息产生记录时间")


class AIUsage(Identity, Base):
    __tablename__ = "ai_usage"
    __table_args__ = {"comment": "AI大模型推理用量与计费审计表"}
    purpose: Mapped[str] = mapped_column(String(50), nullable=False, comment="业务调用场景(chat=智能问答, exception_analysis=异常分析, dashboard_summary=运营看板摘要, decision=决策路由)")
    entity_id: Mapped[str | None] = mapped_column(String(36), comment="关联的业务实体ID(运单/异常/会话等)")
    provider: Mapped[str] = mapped_column(String(50), nullable=False, comment="大模型提供方网关标识")
    model: Mapped[str | None] = mapped_column(String(100), comment="实际调用的模型名称标识")
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="输入Prompt Token消耗计数")
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="输出Completion Token消耗计数")
    cost: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False, default=0, comment="推理计费金额(人民币元)")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="调用审计发生时间")


class KnowledgeDocument(Identity, Timestamped, Base):
    __tablename__ = "knowledge_documents"
    __table_args__ = {"comment": "业务知识库文档档案表"}
    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="知识库文档标题")
    source_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="文档来源类型(manual=手动录入, upload=文件上传, system=系统集成)")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="文档全文文本内容")
    embedding: Mapped[list[float] | None] = mapped_column(EmbeddingType, comment="整篇文档的全局向量嵌入")
    extra_metadata: Mapped[dict] = mapped_column("metadata", JsonType, nullable=False, default=dict, comment="文档扩展元数据(如原始文件属性、分类等)")


class KnowledgeChunk(Identity, Base):
    __tablename__ = "knowledge_chunks"
    __table_args__ = {"comment": "知识库文档分块切片向量表"}
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("knowledge_documents.id"), nullable=False, index=True, comment="所属知识库文档ID")
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, comment="分块切片在文档内的顺序编号(0起步)")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="该切片文本片段内容")
    embedding: Mapped[list[float]] = mapped_column(EmbeddingType, nullable=False, comment="切片文本对应的1536维语义向量")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="切片建立时间")


Index("ix_exception_tenant_status", LogisticsException.tenant_id, LogisticsException.status)
Index("ix_shipment_tenant_status", Shipment.tenant_id, Shipment.status)
