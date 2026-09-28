<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { platform, type LogisticsException } from '../api/platform'
import { errorMessage } from '../utils/errors'
import { formatDateTime } from '../utils/datetime'

const rows = ref<LogisticsException[]>([])
const total = ref(0)
const page = ref(1)
const status = ref('')
const level = ref('')
const type = ref('')
const loading = ref(false)
const types = ['DEPARTURE_DELAY','ARRIVAL_DELAY','TRACKING_STALE','UNSIGNED_TOO_LONG','DATA_MISSING']
async function load() { loading.value = true; try { const data = await platform.exceptions({status:status.value, level:level.value, type:type.value, offset:(page.value - 1) * 20, limit:20}); rows.value = data.items; total.value = data.total } catch (error) { ElMessage.error(errorMessage(error)) } finally { loading.value = false } }
function filter() { page.value = 1; load() }
onMounted(load)
</script>

<template>
  <div class="page-heading"><div><p class="eyebrow">EXCEPTION CENTER</p><h1>异常中心</h1><p class="muted">按风险等级跟进物流异常</p></div></div>
  <div class="panel"><div class="filters"><el-select v-model="status" placeholder="全部状态" clearable style="width:145px" @change="filter"><el-option label="待处理" value="open" /><el-option label="已解决" value="resolved" /></el-select><el-select v-model="level" placeholder="全部等级" clearable style="width:145px" @change="filter"><el-option v-for="item in ['LOW','MEDIUM','HIGH','CRITICAL']" :key="item" :label="item" :value="item" /></el-select><el-select v-model="type" placeholder="全部类型" clearable style="width:220px" @change="filter"><el-option v-for="item in types" :key="item" :label="item" :value="item" /></el-select></div>
    <el-table v-loading="loading" :data="rows" stripe><el-table-column label="类型" width="190"><template #default="scope"><RouterLink :to="`/exceptions/${scope.row.id}`" class="table-link">{{ scope.row.type }}</RouterLink></template></el-table-column><el-table-column label="等级" width="110"><template #default="scope"><el-tag :type="scope.row.level === 'HIGH' || scope.row.level === 'CRITICAL' ? 'danger' : 'warning'">{{ scope.row.level }}</el-tag></template></el-table-column><el-table-column prop="status" label="状态" width="100" /><el-table-column prop="reason" label="触发原因" min-width="340" show-overflow-tooltip /><el-table-column label="发现时间" min-width="190"><template #default="scope">{{ formatDateTime(scope.row.detected_at) }}</template></el-table-column></el-table><div class="pagination"><el-pagination v-model:current-page="page" background layout="total, prev, pager, next" :total="total" :page-size="20" @current-change="load" /></div>
  </div>
</template>
