<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { platform, type Shipment } from '../api/platform'
import { errorMessage } from '../utils/errors'
import { formatDateTime } from '../utils/datetime'

const rows = ref<Shipment[]>([])
const total = ref(0)
const page = ref(1)
const search = ref('')
const status = ref('')
const loading = ref(false)
const statuses = ['CREATED','READY','PICKED_UP','IN_TRANSIT','ARRIVED','DELIVERING','DELIVERED','CANCELLED','UNKNOWN']
async function load() { loading.value = true; try { const data = await platform.shipments({search:search.value, status:status.value, offset:(page.value - 1) * 20, limit:20}); rows.value = data.items; total.value = data.total } catch (error) { ElMessage.error(errorMessage(error)) } finally { loading.value = false } }
function filter() { page.value = 1; load() }
onMounted(load)
</script>

<template>
  <div class="page-heading"><div><p class="eyebrow">SHIPMENT CENTER</p><h1>运单中心</h1><p class="muted">统一查看来自不同系统的标准运单</p></div></div>
  <div class="panel"><div class="filters"><el-input v-model="search" placeholder="运单号、起点或终点" clearable style="width:260px" @keyup.enter="filter" /><el-select v-model="status" placeholder="全部状态" clearable style="width:170px" @change="filter"><el-option v-for="item in statuses" :key="item" :label="item" :value="item" /></el-select><el-button type="primary" @click="filter">查询</el-button></div>
    <el-table v-loading="loading" :data="rows" stripe><el-table-column prop="shipment_no" label="运单号" min-width="160"><template #default="scope"><RouterLink :to="`/shipments/${scope.row.id}`" class="table-link">{{ scope.row.shipment_no }}</RouterLink></template></el-table-column><el-table-column prop="status" label="状态" width="140" /><el-table-column prop="origin" label="起点" min-width="130" /><el-table-column prop="destination" label="终点" min-width="130" /><el-table-column label="计划到达" min-width="190"><template #default="scope">{{ formatDateTime(scope.row.planned_arrival_time) }}</template></el-table-column><el-table-column label="入库时间" min-width="190"><template #default="scope">{{ formatDateTime(scope.row.created_at) }}</template></el-table-column></el-table><div class="pagination"><el-pagination v-model:current-page="page" background layout="total, prev, pager, next" :total="total" :page-size="20" @current-change="load" /></div>
  </div>
</template>
