<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { platform, type Connector, type Mapping } from '../api/platform'
import { errorMessage } from '../utils/errors'

interface Row extends Mapping { transformText: string }
const id = String(useRoute().params.id)
const connector = ref<Connector | null>(null)
const rows = ref<Row[]>([])
const sample = ref<Record<string, unknown>[]>([])
const fields = ref<string[]>([])
const saving = ref(false)
const targets = ['shipment_no', 'external_id', 'status', 'origin', 'destination', 'sender_name', 'receiver_name', 'planned_departure_time', 'actual_departure_time', 'planned_arrival_time', 'actual_arrival_time', 'latest_tracking_time', 'signed_at', 'driver_external_id', 'vehicle_plate_no', 'route_name']
const suggestions: Record<string, string> = {waybillNo:'shipment_no', order_id:'shipment_no', shipment_no:'shipment_no', status:'status', state:'status', fromArea:'origin', origin:'origin', toArea:'destination', destination:'destination', sendName:'sender_name', sender:'sender_name', receiveName:'receiver_name', consignee:'receiver_name', planDepart:'planned_departure_time', actualDepart:'actual_departure_time', planArrive:'planned_arrival_time', actualArrive:'actual_arrival_time', driverCode:'driver_external_id', plateNo:'vehicle_plate_no', routeName:'route_name'}
function add() { rows.value.push({source_field:'', target_field:'', transform:{}, transformText:'{}', required:false}) }
async function loadSample() { try { const data = await platform.sampleConnector(id); sample.value = data.rows; fields.value = data.fields; sessionStorage.setItem(`sample_${id}`, JSON.stringify(data)); if (!rows.value.length) suggest() } catch (error) { ElMessage.error(errorMessage(error)) } }
function suggest() { rows.value = fields.value.map(field => ({source_field: field, target_field: suggestions[field] || '', transform: {}, transformText: '{}', required: field === 'waybillNo' || field === 'shipment_no'})).filter(item => item.target_field) }
async function save() { saving.value = true; try { const mappings = rows.value.filter(item => item.source_field && item.target_field).map(item => ({source_field:item.source_field, target_field:item.target_field, required:item.required, transform:JSON.parse(item.transformText)})); await platform.saveMappings(id, mappings); ElMessage.success('字段映射已保存') } catch (error) { ElMessage.error(errorMessage(error)) } finally { saving.value = false } }
onMounted(async () => { try { connector.value = await platform.connector(id); const saved = await platform.mappings(id); rows.value = saved.map(item => ({...item, transformText: JSON.stringify(item.transform || {})})); const cached = sessionStorage.getItem(`sample_${id}`); if (cached) { const data = JSON.parse(cached); sample.value = data.rows; fields.value = data.fields; if (!rows.value.length) suggest() } } catch (error) { ElMessage.error(errorMessage(error)) } })
</script>

<template>
  <div class="page-heading"><div><p class="eyebrow">FIELD MAPPING</p><h1>{{ connector?.name }} · 字段映射</h1><p class="muted">将来源字段转换为平台统一运单字段</p></div><RouterLink :to="`/connectors/${id}`"><el-button>返回连接器</el-button></RouterLink></div>
  <div class="panel"><div class="actions"><el-button v-if="connector?.type === 'rest'" @click="loadSample">获取并识别样例</el-button><el-button @click="add">添加映射</el-button><el-button type="primary" :loading="saving" @click="save">保存映射</el-button></div>
    <p class="form-hint">shipment_no 必填。状态转换示例：<code>{"values":{"30":"IN_TRANSIT","40":"DELIVERED"}}</code></p>
    <el-table :data="rows" stripe><el-table-column label="来源字段" min-width="160"><template #default="scope"><el-input v-model="scope.row.source_field" placeholder="waybillNo" /></template></el-table-column><el-table-column label="目标字段" min-width="190"><template #default="scope"><el-select v-model="scope.row.target_field" filterable style="width:100%"><el-option v-for="target in targets" :key="target" :label="target" :value="target" /></el-select></template></el-table-column><el-table-column label="转换 JSON" min-width="270"><template #default="scope"><el-input v-model="scope.row.transformText" /></template></el-table-column><el-table-column label="必填" width="80"><template #default="scope"><el-switch v-model="scope.row.required" /></template></el-table-column><el-table-column label="" width="75"><template #default="scope"><el-button text type="danger" @click="rows.splice(scope.$index, 1)">删除</el-button></template></el-table-column></el-table>
    <div v-if="sample.length" class="input-section"><strong>样例数据</strong><pre>{{ JSON.stringify(sample[0], null, 2) }}</pre></div>
  </div>
</template>
