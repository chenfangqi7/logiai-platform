<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { platform, type LogisticsException, type Shipment } from '../api/platform'
import { errorMessage } from '../utils/errors'
import { formatDateTime } from '../utils/datetime'

const id = String(useRoute().params.id)
type Detail = Shipment & { tracking_events: Record<string, unknown>[]; exceptions: LogisticsException[]; driver: Record<string, unknown> | null; vehicle: Record<string, unknown> | null; route: Record<string, unknown> | null; source_connector: {id: string; name: string} | null }
const detail = ref<Detail | null>(null)
onMounted(async () => { try { detail.value = await platform.shipment(id) } catch (error) { ElMessage.error(errorMessage(error)) } })
</script>

<template>
  <div class="page-heading"><div><p class="eyebrow">SHIPMENT DETAIL</p><h1>{{ detail?.shipment_no || '运单详情' }}</h1><p class="muted">{{ detail?.origin }} → {{ detail?.destination }}</p></div><RouterLink to="/shipments"><el-button>返回列表</el-button></RouterLink></div>
  <template v-if="detail"><div class="panel"><div class="panel-title">运单信息</div><el-descriptions :column="2" border><el-descriptions-item label="状态">{{ detail.status }}</el-descriptions-item><el-descriptions-item label="线路">{{ detail.route?.name || '—' }}</el-descriptions-item><el-descriptions-item label="司机">{{ detail.driver?.name || '—' }}</el-descriptions-item><el-descriptions-item label="车辆">{{ detail.vehicle?.plate_no || '—' }}</el-descriptions-item><el-descriptions-item label="计划发车">{{ formatDateTime(detail.planned_departure_time) }}</el-descriptions-item><el-descriptions-item label="计划到达">{{ formatDateTime(detail.planned_arrival_time) }}</el-descriptions-item></el-descriptions></div>
    <div class="two-column"><section class="panel"><div class="panel-title">轨迹时间线</div><el-timeline><el-timeline-item v-for="(event, index) in detail.tracking_events" :key="index" :timestamp="formatDateTime(String(event.event_time))">{{ event.event_type }} · {{ event.location }}</el-timeline-item></el-timeline><p v-if="!detail.tracking_events.length" class="muted">暂无轨迹</p></section><section class="panel"><div class="panel-title">关联异常</div><RouterLink v-for="item in detail.exceptions" :key="item.id" :to="`/exceptions/${item.id}`" class="recent-row"><span>{{ item.type }} · {{ item.reason }}</span><el-tag size="small">{{ item.level }}</el-tag></RouterLink><p v-if="!detail.exceptions.length" class="muted">暂无异常</p></section></div>
    <div class="panel"><div class="panel-title">数据来源</div><el-descriptions :column="2" border><el-descriptions-item label="Connector">{{ detail.source_connector?.name || '—' }}</el-descriptions-item><el-descriptions-item label="外部 ID">{{ detail.source_external_id || '—' }}</el-descriptions-item><el-descriptions-item label="来源更新时间">{{ formatDateTime(detail.source_updated_at) }}</el-descriptions-item><el-descriptions-item label="最后同步">{{ formatDateTime(detail.last_synced_at) }}</el-descriptions-item></el-descriptions></div>
    <div class="panel"><div class="panel-title">原始来源数据</div><pre>{{ JSON.stringify(detail.raw_data, null, 2) }}</pre></div>
  </template>
</template>
