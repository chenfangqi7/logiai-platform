"""Add table and column comments for data governance and dictionary documentation.

Revision ID: 0011_table_column_comments
Revises: 0010_encrypt_custom_headers
"""

from alembic import op

revision = "0011_table_column_comments"
down_revision = "0010_encrypt_custom_headers"
branch_labels = None
depends_on = None

COMMENTS = [
    # 1. tenants
    ("COMMENT ON TABLE tenants IS '租户信息表';", "COMMENT ON TABLE tenants IS NULL;"),
    ("COMMENT ON COLUMN tenants.id IS '租户唯一主键UUID';", "COMMENT ON COLUMN tenants.id IS NULL;"),
    ("COMMENT ON COLUMN tenants.name IS '租户企业名称';", "COMMENT ON COLUMN tenants.name IS NULL;"),
    ("COMMENT ON COLUMN tenants.code IS '租户唯一英文编码标识';", "COMMENT ON COLUMN tenants.code IS NULL;"),
    ("COMMENT ON COLUMN tenants.status IS '租户状态(active=启用, disabled=禁用)';", "COMMENT ON COLUMN tenants.status IS NULL;"),
    ("COMMENT ON COLUMN tenants.created_at IS '记录创建时间';", "COMMENT ON COLUMN tenants.created_at IS NULL;"),
    ("COMMENT ON COLUMN tenants.updated_at IS '最后更新时间';", "COMMENT ON COLUMN tenants.updated_at IS NULL;"),

    # 2. users
    ("COMMENT ON TABLE users IS '系统用户信息表';", "COMMENT ON TABLE users IS NULL;"),
    ("COMMENT ON COLUMN users.id IS '用户唯一主键UUID';", "COMMENT ON COLUMN users.id IS NULL;"),
    ("COMMENT ON COLUMN users.tenant_id IS '所属租户ID';", "COMMENT ON COLUMN users.tenant_id IS NULL;"),
    ("COMMENT ON COLUMN users.username IS '登录账号/用户名';", "COMMENT ON COLUMN users.username IS NULL;"),
    ("COMMENT ON COLUMN users.email IS '电子邮箱地址';", "COMMENT ON COLUMN users.email IS NULL;"),
    ("COMMENT ON COLUMN users.password_hash IS '加密密码散列值';", "COMMENT ON COLUMN users.password_hash IS NULL;"),
    ("COMMENT ON COLUMN users.role IS '用户角色(admin=管理员, member=普通成员)';", "COMMENT ON COLUMN users.role IS NULL;"),
    ("COMMENT ON COLUMN users.status IS '用户状态(active=启用, disabled=禁用)';", "COMMENT ON COLUMN users.status IS NULL;"),
    ("COMMENT ON COLUMN users.created_at IS '记录创建时间';", "COMMENT ON COLUMN users.created_at IS NULL;"),
    ("COMMENT ON COLUMN users.updated_at IS '最后更新时间';", "COMMENT ON COLUMN users.updated_at IS NULL;"),

    # 3. connectors
    ("COMMENT ON TABLE connectors IS '数据连接器配置表';", "COMMENT ON TABLE connectors IS NULL;"),
    ("COMMENT ON COLUMN connectors.id IS '连接器唯一主键UUID';", "COMMENT ON COLUMN connectors.id IS NULL;"),
    ("COMMENT ON COLUMN connectors.tenant_id IS '所属租户ID';", "COMMENT ON COLUMN connectors.tenant_id IS NULL;"),
    ("COMMENT ON COLUMN connectors.name IS '连接器名称';", "COMMENT ON COLUMN connectors.name IS NULL;"),
    ("COMMENT ON COLUMN connectors.type IS '连接器类型(rest=API接口, database=数据库, file=文件导入, webhook=回调接收)';", "COMMENT ON COLUMN connectors.type IS NULL;"),
    ("COMMENT ON COLUMN connectors.base_url IS '服务接入基础URL地址';", "COMMENT ON COLUMN connectors.base_url IS NULL;"),
    ("COMMENT ON COLUMN connectors.auth_type IS '认证方式(none=无, basic=BasicAuth, bearer=BearerToken, api_key=API密钥)';", "COMMENT ON COLUMN connectors.auth_type IS NULL;"),
    ("COMMENT ON COLUMN connectors.config IS '连接器详细配置与凭证参数(加密存储)';", "COMMENT ON COLUMN connectors.config IS NULL;"),
    ("COMMENT ON COLUMN connectors.status IS '连接器状态(active=启用, inactive=停用, error=异常)';", "COMMENT ON COLUMN connectors.status IS NULL;"),
    ("COMMENT ON COLUMN connectors.created_at IS '记录创建时间';", "COMMENT ON COLUMN connectors.created_at IS NULL;"),
    ("COMMENT ON COLUMN connectors.updated_at IS '最后更新时间';", "COMMENT ON COLUMN connectors.updated_at IS NULL;"),

    # 4. field_mappings
    ("COMMENT ON TABLE field_mappings IS '数据字段映射规则表';", "COMMENT ON TABLE field_mappings IS NULL;"),
    ("COMMENT ON COLUMN field_mappings.id IS '映射规则唯一主键UUID';", "COMMENT ON COLUMN field_mappings.id IS NULL;"),
    ("COMMENT ON COLUMN field_mappings.tenant_id IS '所属租户ID';", "COMMENT ON COLUMN field_mappings.tenant_id IS NULL;"),
    ("COMMENT ON COLUMN field_mappings.connector_id IS '关联连接器ID';", "COMMENT ON COLUMN field_mappings.connector_id IS NULL;"),
    ("COMMENT ON COLUMN field_mappings.entity_type IS '目标实体对象类型(shipment=运单, event=轨迹事件, vehicle=车辆, driver=司机)';", "COMMENT ON COLUMN field_mappings.entity_type IS NULL;"),
    ("COMMENT ON COLUMN field_mappings.source_field IS '外部源数据字段路径';", "COMMENT ON COLUMN field_mappings.source_field IS NULL;"),
    ("COMMENT ON COLUMN field_mappings.target_field IS '系统标准模型目标字段名';", "COMMENT ON COLUMN field_mappings.target_field IS NULL;"),
    ("COMMENT ON COLUMN field_mappings.transform IS '字段转换规则配置(日期解析、枚举映射、默认值等)';", "COMMENT ON COLUMN field_mappings.transform IS NULL;"),
    ("COMMENT ON COLUMN field_mappings.required IS '是否为必填关键字段';", "COMMENT ON COLUMN field_mappings.required IS NULL;"),
    ("COMMENT ON COLUMN field_mappings.created_at IS '记录创建时间';", "COMMENT ON COLUMN field_mappings.created_at IS NULL;"),
    ("COMMENT ON COLUMN field_mappings.updated_at IS '最后更新时间';", "COMMENT ON COLUMN field_mappings.updated_at IS NULL;"),

    # 5. collection_mappings
    ("COMMENT ON TABLE collection_mappings IS '集合嵌套对象映射配置表';", "COMMENT ON TABLE collection_mappings IS NULL;"),
    ("COMMENT ON COLUMN collection_mappings.id IS '集合映射唯一主键UUID';", "COMMENT ON COLUMN collection_mappings.id IS NULL;"),
    ("COMMENT ON COLUMN collection_mappings.tenant_id IS '所属租户ID';", "COMMENT ON COLUMN collection_mappings.tenant_id IS NULL;"),
    ("COMMENT ON COLUMN collection_mappings.connector_id IS '关联连接器ID';", "COMMENT ON COLUMN collection_mappings.connector_id IS NULL;"),
    ("COMMENT ON COLUMN collection_mappings.source_field IS '外部源数据中嵌套数组集合字段名(如events)';", "COMMENT ON COLUMN collection_mappings.source_field IS NULL;"),
    ("COMMENT ON COLUMN collection_mappings.target_entity IS '映射的目标集合实体名(如tracking_events)';", "COMMENT ON COLUMN collection_mappings.target_entity IS NULL;"),
    ("COMMENT ON COLUMN collection_mappings.fields IS '集合内部子字段映射规则列表';", "COMMENT ON COLUMN collection_mappings.fields IS NULL;"),
    ("COMMENT ON COLUMN collection_mappings.created_at IS '记录创建时间';", "COMMENT ON COLUMN collection_mappings.created_at IS NULL;"),
    ("COMMENT ON COLUMN collection_mappings.updated_at IS '最后更新时间';", "COMMENT ON COLUMN collection_mappings.updated_at IS NULL;"),

    # 6. sync_jobs
    ("COMMENT ON TABLE sync_jobs IS '数据同步任务记录表';", "COMMENT ON TABLE sync_jobs IS NULL;"),
    ("COMMENT ON COLUMN sync_jobs.id IS '同步任务唯一主键UUID';", "COMMENT ON COLUMN sync_jobs.id IS NULL;"),
    ("COMMENT ON COLUMN sync_jobs.tenant_id IS '所属租户ID';", "COMMENT ON COLUMN sync_jobs.tenant_id IS NULL;"),
    ("COMMENT ON COLUMN sync_jobs.connector_id IS '关联连接器ID';", "COMMENT ON COLUMN sync_jobs.connector_id IS NULL;"),
    ("COMMENT ON COLUMN sync_jobs.status IS '任务执行状态(PENDING=待运行, RUNNING=执行中, SUCCESS=成功, FAILED=失败, PARTIAL=部分成功)';", "COMMENT ON COLUMN sync_jobs.status IS NULL;"),
    ("COMMENT ON COLUMN sync_jobs.started_at IS '任务开始执行时间';", "COMMENT ON COLUMN sync_jobs.started_at IS NULL;"),
    ("COMMENT ON COLUMN sync_jobs.finished_at IS '任务结束完成时间';", "COMMENT ON COLUMN sync_jobs.finished_at IS NULL;"),
    ("COMMENT ON COLUMN sync_jobs.total_count IS '本次待同步总数据条数';", "COMMENT ON COLUMN sync_jobs.total_count IS NULL;"),
    ("COMMENT ON COLUMN sync_jobs.success_count IS '成功同步写入数据条数';", "COMMENT ON COLUMN sync_jobs.success_count IS NULL;"),
    ("COMMENT ON COLUMN sync_jobs.failed_count IS '失败或校验未通过数据条数';", "COMMENT ON COLUMN sync_jobs.failed_count IS NULL;"),
    ("COMMENT ON COLUMN sync_jobs.result IS '任务执行统计与处理结果摘要';", "COMMENT ON COLUMN sync_jobs.result IS NULL;"),
    ("COMMENT ON COLUMN sync_jobs.error_message IS '执行失败时的错误摘要信息';", "COMMENT ON COLUMN sync_jobs.error_message IS NULL;"),
    ("COMMENT ON COLUMN sync_jobs.created_at IS '任务创建时间';", "COMMENT ON COLUMN sync_jobs.created_at IS NULL;"),

    # 7. sync_issues
    ("COMMENT ON TABLE sync_issues IS '数据同步问题与校验异常明细表';", "COMMENT ON TABLE sync_issues IS NULL;"),
    ("COMMENT ON COLUMN sync_issues.id IS '异常明细唯一主键UUID';", "COMMENT ON COLUMN sync_issues.id IS NULL;"),
    ("COMMENT ON COLUMN sync_issues.tenant_id IS '所属租户ID';", "COMMENT ON COLUMN sync_issues.tenant_id IS NULL;"),
    ("COMMENT ON COLUMN sync_issues.job_id IS '关联同步任务ID';", "COMMENT ON COLUMN sync_issues.job_id IS NULL;"),
    ("COMMENT ON COLUMN sync_issues.connector_id IS '关联连接器ID';", "COMMENT ON COLUMN sync_issues.connector_id IS NULL;"),
    ("COMMENT ON COLUMN sync_issues.row_number IS '原始数据行号或记录序号';", "COMMENT ON COLUMN sync_issues.row_number IS NULL;"),
    ("COMMENT ON COLUMN sync_issues.entity IS '异常发生的目标实体类型';", "COMMENT ON COLUMN sync_issues.entity IS NULL;"),
    ("COMMENT ON COLUMN sync_issues.external_id IS '外部源数据原始单号或业务主键';", "COMMENT ON COLUMN sync_issues.external_id IS NULL;"),
    ("COMMENT ON COLUMN sync_issues.level IS '问题严重级别(WARNING=警告, ERROR=错误)';", "COMMENT ON COLUMN sync_issues.level IS NULL;"),
    ("COMMENT ON COLUMN sync_issues.code IS '异常错误分类编码';", "COMMENT ON COLUMN sync_issues.code IS NULL;"),
    ("COMMENT ON COLUMN sync_issues.message IS '详细错误原因说明';", "COMMENT ON COLUMN sync_issues.message IS NULL;"),
    ("COMMENT ON COLUMN sync_issues.created_at IS '记录创建时间';", "COMMENT ON COLUMN sync_issues.created_at IS NULL;"),

    # 8. vehicles
    ("COMMENT ON TABLE vehicles IS '运力车辆信息表';", "COMMENT ON TABLE vehicles IS NULL;"),
    ("COMMENT ON COLUMN vehicles.id IS '车辆唯一主键UUID';", "COMMENT ON COLUMN vehicles.id IS NULL;"),
    ("COMMENT ON COLUMN vehicles.tenant_id IS '所属租户ID';", "COMMENT ON COLUMN vehicles.tenant_id IS NULL;"),
    ("COMMENT ON COLUMN vehicles.external_id IS '外部系统车辆原始业务主键';", "COMMENT ON COLUMN vehicles.external_id IS NULL;"),
    ("COMMENT ON COLUMN vehicles.plate_no IS '车辆牌照号码';", "COMMENT ON COLUMN vehicles.plate_no IS NULL;"),
    ("COMMENT ON COLUMN vehicles.vehicle_type IS '车型分类(如4.2米箱货、9.6米高栏、17.5米平板)';", "COMMENT ON COLUMN vehicles.vehicle_type IS NULL;"),
    ("COMMENT ON COLUMN vehicles.status IS '车辆运营状态(active=运营中, maintenance=维修中, retired=已停用)';", "COMMENT ON COLUMN vehicles.status IS NULL;"),
    ("COMMENT ON COLUMN vehicles.raw_data IS '外部原始数据快照';", "COMMENT ON COLUMN vehicles.raw_data IS NULL;"),
    ("COMMENT ON COLUMN vehicles.created_at IS '记录创建时间';", "COMMENT ON COLUMN vehicles.created_at IS NULL;"),
    ("COMMENT ON COLUMN vehicles.updated_at IS '最后更新时间';", "COMMENT ON COLUMN vehicles.updated_at IS NULL;"),

    # 9. drivers
    ("COMMENT ON TABLE drivers IS '司机运力人员信息表';", "COMMENT ON TABLE drivers IS NULL;"),
    ("COMMENT ON COLUMN drivers.id IS '司机唯一主键UUID';", "COMMENT ON COLUMN drivers.id IS NULL;"),
    ("COMMENT ON COLUMN drivers.tenant_id IS '所属租户ID';", "COMMENT ON COLUMN drivers.tenant_id IS NULL;"),
    ("COMMENT ON COLUMN drivers.external_id IS '外部系统司机原始业务主键';", "COMMENT ON COLUMN drivers.external_id IS NULL;"),
    ("COMMENT ON COLUMN drivers.name IS '司机姓名';", "COMMENT ON COLUMN drivers.name IS NULL;"),
    ("COMMENT ON COLUMN drivers.phone IS '司机联系手机号码';", "COMMENT ON COLUMN drivers.phone IS NULL;"),
    ("COMMENT ON COLUMN drivers.status IS '司机工作状态(active=在职接单, resting=休息中, inactive=已离职)';", "COMMENT ON COLUMN drivers.status IS NULL;"),
    ("COMMENT ON COLUMN drivers.raw_data IS '外部原始数据快照';", "COMMENT ON COLUMN drivers.raw_data IS NULL;"),
    ("COMMENT ON COLUMN drivers.created_at IS '记录创建时间';", "COMMENT ON COLUMN drivers.created_at IS NULL;"),
    ("COMMENT ON COLUMN drivers.updated_at IS '最后更新时间';", "COMMENT ON COLUMN drivers.updated_at IS NULL;"),

    # 10. routes
    ("COMMENT ON TABLE routes IS '运输线路规划信息表';", "COMMENT ON TABLE routes IS NULL;"),
    ("COMMENT ON COLUMN routes.id IS '线路唯一主键UUID';", "COMMENT ON COLUMN routes.id IS NULL;"),
    ("COMMENT ON COLUMN routes.tenant_id IS '所属租户ID';", "COMMENT ON COLUMN routes.tenant_id IS NULL;"),
    ("COMMENT ON COLUMN routes.name IS '线路名称(如华东干线-沪京线)';", "COMMENT ON COLUMN routes.name IS NULL;"),
    ("COMMENT ON COLUMN routes.origin IS '起点城市/始发枢纽仓';", "COMMENT ON COLUMN routes.origin IS NULL;"),
    ("COMMENT ON COLUMN routes.destination IS '终点城市/目的配送中心';", "COMMENT ON COLUMN routes.destination IS NULL;"),
    ("COMMENT ON COLUMN routes.status IS '线路启用状态(active=有效运营, inactive=暂停运营)';", "COMMENT ON COLUMN routes.status IS NULL;"),
    ("COMMENT ON COLUMN routes.created_at IS '记录创建时间';", "COMMENT ON COLUMN routes.created_at IS NULL;"),
    ("COMMENT ON COLUMN routes.updated_at IS '最后更新时间';", "COMMENT ON COLUMN routes.updated_at IS NULL;"),

    # 11. shipments
    ("COMMENT ON TABLE shipments IS '物流运单业务主表';", "COMMENT ON TABLE shipments IS NULL;"),
    ("COMMENT ON COLUMN shipments.id IS '运单唯一主键UUID';", "COMMENT ON COLUMN shipments.id IS NULL;"),
    ("COMMENT ON COLUMN shipments.tenant_id IS '所属租户ID';", "COMMENT ON COLUMN shipments.tenant_id IS NULL;"),
    ("COMMENT ON COLUMN shipments.shipment_no IS '系统标准运单唯一跟踪编号';", "COMMENT ON COLUMN shipments.shipment_no IS NULL;"),
    ("COMMENT ON COLUMN shipments.external_id IS '外部TMS/ERP系统原始运单编号';", "COMMENT ON COLUMN shipments.external_id IS NULL;"),
    ("COMMENT ON COLUMN shipments.source_connector_id IS '接入来源连接器ID';", "COMMENT ON COLUMN shipments.source_connector_id IS NULL;"),
    ("COMMENT ON COLUMN shipments.source_external_id IS '外部源系统的全局唯一业务记录主键';", "COMMENT ON COLUMN shipments.source_external_id IS NULL;"),
    ("COMMENT ON COLUMN shipments.source_updated_at IS '外部系统源数据最新更新时间';", "COMMENT ON COLUMN shipments.source_updated_at IS NULL;"),
    ("COMMENT ON COLUMN shipments.last_synced_at IS '本系统最近一次成功同步写入时间';", "COMMENT ON COLUMN shipments.last_synced_at IS NULL;"),
    ("COMMENT ON COLUMN shipments.status IS '运单当前生命周期状态(CREATED=已创建, DISPATCHED=已调度, IN_TRANSIT=运输中, ARRIVED=已到达, DELIVERED=已签收, EXCEPTION=异常阻断, CANCELLED=已取消)';", "COMMENT ON COLUMN shipments.status IS NULL;"),
    ("COMMENT ON COLUMN shipments.origin IS '始发地点或发货网点';", "COMMENT ON COLUMN shipments.origin IS NULL;"),
    ("COMMENT ON COLUMN shipments.destination IS '目的地点或收货网点';", "COMMENT ON COLUMN shipments.destination IS NULL;"),
    ("COMMENT ON COLUMN shipments.sender_name IS '发货人或发货单位名称';", "COMMENT ON COLUMN shipments.sender_name IS NULL;"),
    ("COMMENT ON COLUMN shipments.receiver_name IS '收货人或收货单位名称';", "COMMENT ON COLUMN shipments.receiver_name IS NULL;"),
    ("COMMENT ON COLUMN shipments.planned_departure_time IS '计划发货启运时间';", "COMMENT ON COLUMN shipments.planned_departure_time IS NULL;"),
    ("COMMENT ON COLUMN shipments.actual_departure_time IS '实际发车出库时间';", "COMMENT ON COLUMN shipments.actual_departure_time IS NULL;"),
    ("COMMENT ON COLUMN shipments.planned_arrival_time IS '预计到达签收时间';", "COMMENT ON COLUMN shipments.planned_arrival_time IS NULL;"),
    ("COMMENT ON COLUMN shipments.actual_arrival_time IS '实际运抵终点时间';", "COMMENT ON COLUMN shipments.actual_arrival_time IS NULL;"),
    ("COMMENT ON COLUMN shipments.latest_tracking_time IS '最新物流轨迹上报时间';", "COMMENT ON COLUMN shipments.latest_tracking_time IS NULL;"),
    ("COMMENT ON COLUMN shipments.signed_at IS '收货人确认签收时间';", "COMMENT ON COLUMN shipments.signed_at IS NULL;"),
    ("COMMENT ON COLUMN shipments.driver_id IS '承运关联司机ID';", "COMMENT ON COLUMN shipments.driver_id IS NULL;"),
    ("COMMENT ON COLUMN shipments.vehicle_id IS '承运关联车辆ID';", "COMMENT ON COLUMN shipments.vehicle_id IS NULL;"),
    ("COMMENT ON COLUMN shipments.route_id IS '规划运输线路ID';", "COMMENT ON COLUMN shipments.route_id IS NULL;"),
    ("COMMENT ON COLUMN shipments.raw_data IS '外部原始业务报文JSON快照';", "COMMENT ON COLUMN shipments.raw_data IS NULL;"),
    ("COMMENT ON COLUMN shipments.created_at IS '记录创建时间';", "COMMENT ON COLUMN shipments.created_at IS NULL;"),
    ("COMMENT ON COLUMN shipments.updated_at IS '最后更新时间';", "COMMENT ON COLUMN shipments.updated_at IS NULL;"),

    # 12. tracking_events
    ("COMMENT ON TABLE tracking_events IS '运单物流轨迹事件流水表';", "COMMENT ON TABLE tracking_events IS NULL;"),
    ("COMMENT ON COLUMN tracking_events.id IS '轨迹事件唯一主键UUID';", "COMMENT ON COLUMN tracking_events.id IS NULL;"),
    ("COMMENT ON COLUMN tracking_events.tenant_id IS '所属租户ID';", "COMMENT ON COLUMN tracking_events.tenant_id IS NULL;"),
    ("COMMENT ON COLUMN tracking_events.shipment_id IS '关联运单ID';", "COMMENT ON COLUMN tracking_events.shipment_id IS NULL;"),
    ("COMMENT ON COLUMN tracking_events.event_type IS '轨迹事件类型(DEPARTURE=发车, CHECKPOINT=途径打卡, TRANSIT=在途中, ARRIVAL=到达, DELIVERY=派送签收)';", "COMMENT ON COLUMN tracking_events.event_type IS NULL;"),
    ("COMMENT ON COLUMN tracking_events.external_event_id IS '外部系统原始轨迹事件唯一流水号';", "COMMENT ON COLUMN tracking_events.external_event_id IS NULL;"),
    ("COMMENT ON COLUMN tracking_events.location IS '轨迹发生地点描述';", "COMMENT ON COLUMN tracking_events.location IS NULL;"),
    ("COMMENT ON COLUMN tracking_events.longitude IS '地理位置经度坐标';", "COMMENT ON COLUMN tracking_events.longitude IS NULL;"),
    ("COMMENT ON COLUMN tracking_events.latitude IS '地理位置纬度坐标';", "COMMENT ON COLUMN tracking_events.latitude IS NULL;"),
    ("COMMENT ON COLUMN tracking_events.event_time IS '轨迹事件发生的业务时间';", "COMMENT ON COLUMN tracking_events.event_time IS NULL;"),
    ("COMMENT ON COLUMN tracking_events.raw_data IS '轨迹原始上报节点数据';", "COMMENT ON COLUMN tracking_events.raw_data IS NULL;"),
    ("COMMENT ON COLUMN tracking_events.created_at IS '数据写入系统时间';", "COMMENT ON COLUMN tracking_events.created_at IS NULL;"),

    # 13. exceptions
    ("COMMENT ON TABLE exceptions IS '物流异常事件及研判处置表';", "COMMENT ON TABLE exceptions IS NULL;"),
    ("COMMENT ON COLUMN exceptions.id IS '异常记录唯一主键UUID';", "COMMENT ON COLUMN exceptions.id IS NULL;"),
    ("COMMENT ON COLUMN exceptions.tenant_id IS '所属租户ID';", "COMMENT ON COLUMN exceptions.tenant_id IS NULL;"),
    ("COMMENT ON COLUMN exceptions.shipment_id IS '关联运单ID';", "COMMENT ON COLUMN exceptions.shipment_id IS NULL;"),
    ("COMMENT ON COLUMN exceptions.type IS '异常分类(DELAY=时效延误, ROUTE_DEVIATION=路线偏离, TEMPERATURE_OUT_OF_RANGE=温控越界, DAMAGE=货损货差, OVERDUE=超期未交付)';", "COMMENT ON COLUMN exceptions.type IS NULL;"),
    ("COMMENT ON COLUMN exceptions.level IS '异常严重级别(LOW=轻微, MEDIUM=中度, HIGH=高危, CRITICAL=紧急告警)';", "COMMENT ON COLUMN exceptions.level IS NULL;"),
    ("COMMENT ON COLUMN exceptions.status IS '异常处理处置状态(open=待处理, in_progress=跟进中, resolved=已解决, closed=已结案忽略)';", "COMMENT ON COLUMN exceptions.status IS NULL;"),
    ("COMMENT ON COLUMN exceptions.rule_code IS '触发此异常的规则策略代码';", "COMMENT ON COLUMN exceptions.rule_code IS NULL;"),
    ("COMMENT ON COLUMN exceptions.reason IS '系统判定的异常成因描述';", "COMMENT ON COLUMN exceptions.reason IS NULL;"),
    ("COMMENT ON COLUMN exceptions.ai_analysis IS 'AI大模型智能研判与根因诊断分析';", "COMMENT ON COLUMN exceptions.ai_analysis IS NULL;"),
    ("COMMENT ON COLUMN exceptions.suggestion IS 'AI大模型或规则引擎推荐的应对处置方案';", "COMMENT ON COLUMN exceptions.suggestion IS NULL;"),
    ("COMMENT ON COLUMN exceptions.detected_at IS '系统初次检测发现异常的时间';", "COMMENT ON COLUMN exceptions.detected_at IS NULL;"),
    ("COMMENT ON COLUMN exceptions.resolved_at IS '异常处置完毕闭环时间';", "COMMENT ON COLUMN exceptions.resolved_at IS NULL;"),
    ("COMMENT ON COLUMN exceptions.created_at IS '记录创建时间';", "COMMENT ON COLUMN exceptions.created_at IS NULL;"),
    ("COMMENT ON COLUMN exceptions.updated_at IS '最后更新时间';", "COMMENT ON COLUMN exceptions.updated_at IS NULL;"),

    # 14. ai_conversations
    ("COMMENT ON TABLE ai_conversations IS 'AI助手会话主题表';", "COMMENT ON TABLE ai_conversations IS NULL;"),
    ("COMMENT ON COLUMN ai_conversations.id IS '会话唯一主键UUID';", "COMMENT ON COLUMN ai_conversations.id IS NULL;"),
    ("COMMENT ON COLUMN ai_conversations.tenant_id IS '所属租户ID';", "COMMENT ON COLUMN ai_conversations.tenant_id IS NULL;"),
    ("COMMENT ON COLUMN ai_conversations.user_id IS '发起会话的用户ID';", "COMMENT ON COLUMN ai_conversations.user_id IS NULL;"),
    ("COMMENT ON COLUMN ai_conversations.title IS '会话主题标题';", "COMMENT ON COLUMN ai_conversations.title IS NULL;"),
    ("COMMENT ON COLUMN ai_conversations.created_at IS '记录创建时间';", "COMMENT ON COLUMN ai_conversations.created_at IS NULL;"),
    ("COMMENT ON COLUMN ai_conversations.updated_at IS '最后更新时间';", "COMMENT ON COLUMN ai_conversations.updated_at IS NULL;"),

    # 15. ai_messages
    ("COMMENT ON TABLE ai_messages IS 'AI助手对话消息明细表';", "COMMENT ON TABLE ai_messages IS NULL;"),
    ("COMMENT ON COLUMN ai_messages.id IS '消息唯一主键UUID';", "COMMENT ON COLUMN ai_messages.id IS NULL;"),
    ("COMMENT ON COLUMN ai_messages.tenant_id IS '所属租户ID';", "COMMENT ON COLUMN ai_messages.tenant_id IS NULL;"),
    ("COMMENT ON COLUMN ai_messages.conversation_id IS '所属对话会话ID';", "COMMENT ON COLUMN ai_messages.conversation_id IS NULL;"),
    ("COMMENT ON COLUMN ai_messages.role IS '消息发送角色(user=用户, assistant=AI模型, system=系统预置)';", "COMMENT ON COLUMN ai_messages.role IS NULL;"),
    ("COMMENT ON COLUMN ai_messages.content IS '消息正文内容';", "COMMENT ON COLUMN ai_messages.content IS NULL;"),
    ("COMMENT ON COLUMN ai_messages.provider IS '模型调用网关或提供方名称';", "COMMENT ON COLUMN ai_messages.provider IS NULL;"),
    ("COMMENT ON COLUMN ai_messages.model IS '实际执行推理的大模型名称';", "COMMENT ON COLUMN ai_messages.model IS NULL;"),
    ("COMMENT ON COLUMN ai_messages.input_tokens IS '本次调用输入的Prompt Token数';", "COMMENT ON COLUMN ai_messages.input_tokens IS NULL;"),
    ("COMMENT ON COLUMN ai_messages.output_tokens IS '本次调用输出的Completion Token数';", "COMMENT ON COLUMN ai_messages.output_tokens IS NULL;"),
    ("COMMENT ON COLUMN ai_messages.cost IS '本次调用预估计费成本(人民币元)';", "COMMENT ON COLUMN ai_messages.cost IS NULL;"),
    ("COMMENT ON COLUMN ai_messages.created_at IS '消息产生记录时间';", "COMMENT ON COLUMN ai_messages.created_at IS NULL;"),

    # 16. ai_usage
    ("COMMENT ON TABLE ai_usage IS 'AI大模型推理用量与计费审计表';", "COMMENT ON TABLE ai_usage IS NULL;"),
    ("COMMENT ON COLUMN ai_usage.id IS '审计记录唯一主键UUID';", "COMMENT ON COLUMN ai_usage.id IS NULL;"),
    ("COMMENT ON COLUMN ai_usage.tenant_id IS '所属租户ID';", "COMMENT ON COLUMN ai_usage.tenant_id IS NULL;"),
    ("COMMENT ON COLUMN ai_usage.purpose IS '业务调用场景(chat=智能问答, exception_analysis=异常分析, dashboard_summary=运营看板摘要, decision=决策路由)';", "COMMENT ON COLUMN ai_usage.purpose IS NULL;"),
    ("COMMENT ON COLUMN ai_usage.entity_id IS '关联的业务实体ID(运单/异常/会话等)';", "COMMENT ON COLUMN ai_usage.entity_id IS NULL;"),
    ("COMMENT ON COLUMN ai_usage.provider IS '大模型提供方网关标识';", "COMMENT ON COLUMN ai_usage.provider IS NULL;"),
    ("COMMENT ON COLUMN ai_usage.model IS '实际调用的模型名称标识';", "COMMENT ON COLUMN ai_usage.model IS NULL;"),
    ("COMMENT ON COLUMN ai_usage.input_tokens IS '输入Prompt Token消耗计数';", "COMMENT ON COLUMN ai_usage.input_tokens IS NULL;"),
    ("COMMENT ON COLUMN ai_usage.output_tokens IS '输出Completion Token消耗计数';", "COMMENT ON COLUMN ai_usage.output_tokens IS NULL;"),
    ("COMMENT ON COLUMN ai_usage.cost IS '推理计费金额(人民币元)';", "COMMENT ON COLUMN ai_usage.cost IS NULL;"),
    ("COMMENT ON COLUMN ai_usage.created_at IS '调用审计发生时间';", "COMMENT ON COLUMN ai_usage.created_at IS NULL;"),

    # 17. knowledge_documents
    ("COMMENT ON TABLE knowledge_documents IS '业务知识库文档档案表';", "COMMENT ON TABLE knowledge_documents IS NULL;"),
    ("COMMENT ON COLUMN knowledge_documents.id IS '知识文档唯一主键UUID';", "COMMENT ON COLUMN knowledge_documents.id IS NULL;"),
    ("COMMENT ON COLUMN knowledge_documents.tenant_id IS '所属租户ID';", "COMMENT ON COLUMN knowledge_documents.tenant_id IS NULL;"),
    ("COMMENT ON COLUMN knowledge_documents.title IS '知识库文档标题';", "COMMENT ON COLUMN knowledge_documents.title IS NULL;"),
    ("COMMENT ON COLUMN knowledge_documents.source_type IS '文档来源类型(manual=手动录入, upload=文件上传, system=系统集成)';", "COMMENT ON COLUMN knowledge_documents.source_type IS NULL;"),
    ("COMMENT ON COLUMN knowledge_documents.content IS '文档全文文本内容';", "COMMENT ON COLUMN knowledge_documents.content IS NULL;"),
    ("COMMENT ON COLUMN knowledge_documents.embedding IS '整篇文档的全局向量嵌入';", "COMMENT ON COLUMN knowledge_documents.embedding IS NULL;"),
    ("COMMENT ON COLUMN knowledge_documents.metadata IS '文档扩展元数据(如原始文件属性、分类等)';", "COMMENT ON COLUMN knowledge_documents.metadata IS NULL;"),
    ("COMMENT ON COLUMN knowledge_documents.created_at IS '记录创建时间';", "COMMENT ON COLUMN knowledge_documents.created_at IS NULL;"),
    ("COMMENT ON COLUMN knowledge_documents.updated_at IS '最后更新时间';", "COMMENT ON COLUMN knowledge_documents.updated_at IS NULL;"),

    # 18. knowledge_chunks
    ("COMMENT ON TABLE knowledge_chunks IS '知识库文档分块切片向量表';", "COMMENT ON TABLE knowledge_chunks IS NULL;"),
    ("COMMENT ON COLUMN knowledge_chunks.id IS '分块切片唯一主键UUID';", "COMMENT ON COLUMN knowledge_chunks.id IS NULL;"),
    ("COMMENT ON COLUMN knowledge_chunks.tenant_id IS '所属租户ID';", "COMMENT ON COLUMN knowledge_chunks.tenant_id IS NULL;"),
    ("COMMENT ON COLUMN knowledge_chunks.document_id IS '所属知识库文档ID';", "COMMENT ON COLUMN knowledge_chunks.document_id IS NULL;"),
    ("COMMENT ON COLUMN knowledge_chunks.chunk_index IS '分块切片在文档内的顺序编号(0起步)';", "COMMENT ON COLUMN knowledge_chunks.chunk_index IS NULL;"),
    ("COMMENT ON COLUMN knowledge_chunks.content IS '该切片文本片段内容';", "COMMENT ON COLUMN knowledge_chunks.content IS NULL;"),
    ("COMMENT ON COLUMN knowledge_chunks.embedding IS '切片文本对应的1536维语义向量';", "COMMENT ON COLUMN knowledge_chunks.embedding IS NULL;"),
    ("COMMENT ON COLUMN knowledge_chunks.created_at IS '切片建立时间';", "COMMENT ON COLUMN knowledge_chunks.created_at IS NULL;"),
]


def upgrade() -> None:
    for up_sql, _ in COMMENTS:
        op.execute(up_sql)


def downgrade() -> None:
    for _, down_sql in reversed(COMMENTS):
        op.execute(down_sql)
