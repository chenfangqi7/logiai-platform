<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { platform, type Connector, type ImportResult, type SyncIssue, type SyncJob } from '../api/platform'
import { errorMessage } from '../utils/errors'
import { formatDateTime } from '../utils/datetime'

const route = useRoute()
const id = String(route.params.id)
const connector = ref<Connector | null>(null)
const sample = ref<Record<string, unknown>[]>([])
const fields = ref<string[]>([])
const file = ref<File | null>(null)
const jsonInput = ref('')
const result = ref<ImportResult | null>(null)
const connectionTest = ref<{status_code: number; latency_ms: number; content_type: string} | null>(null)
const jobs = ref<SyncJob[]>([])
const currentJob = ref<SyncJob | null>(null)
const issues = ref<SyncIssue[]>([])
const busy = ref(false)
let pollTimer: ReturnType<typeof setInterval> | undefined
function chooseFile(event: Event) { file.value = (event.target as HTMLInputElement).files?.[0] || null }
async function run(action: () => Promise<unknown>, success: string) { busy.value = true; try { await action(); ElMessage.success(success) } catch (error) { ElMessage.error(errorMessage(error)) } finally { busy.value = false } }
async function fetchSample() { if (!connector.value) return; const data = connector.value.type === 'file' && file.value ? await platform.fileSample(id, file.value) : await platform.sampleConnector(id); sample.value = data.rows; fields.value = data.fields; sessionStorage.setItem(`sample_${id}`, JSON.stringify(data)) }
async function testConnection() { connectionTest.value = await platform.testConnector(id) }
async function importData() { if (!connector.value) return; if (file.value) result.value = await platform.uploadConnector(id, file.value); else { const parsed: unknown = JSON.parse(jsonInput.value); if (!Array.isArray(parsed)) throw new Error('请输入 JSON 数组'); result.value = await platform.importJson(id, parsed as Record<string, unknown>[]) } }
async function importPasted() { const parsed: unknown = JSON.parse(jsonInput.value); if (!Array.isArray(parsed)) throw new Error('请输入 JSON 数组'); result.value = await platform.importJson(id, parsed as Record<string, unknown>[]) }
async function loadHistory() { jobs.value = await platform.syncJobs(id) }
async function selectJob(jobId: string) { currentJob.value = await platform.syncJob(id, jobId); issues.value = await platform.syncIssues(id, jobId) }
async function pollJob(jobId: string) { try { await selectJob(jobId); if (currentJob.value && !['PENDING', 'RUNNING'].includes(currentJob.value.status)) { if (pollTimer) clearInterval(pollTimer); pollTimer = undefined; await loadHistory() } } catch (error) { if (pollTimer) clearInterval(pollTimer); pollTimer = undefined; ElMessage.error(errorMessage(error)) } }
async function startJob() { busy.value = true; try { const job = await platform.startSyncJob(id); currentJob.value = job; issues.value = []; await loadHistory(); pollTimer = setInterval(() => { void pollJob(job.id) }, 1500); await pollJob(job.id); ElMessage.success('同步作业已创建') } catch (error) { ElMessage.error(errorMessage(error)) } finally { busy.value = false } }
onMounted(async () => { try { connector.value = await platform.connector(id); if (connector.value.type === 'rest') { await loadHistory(); const active = jobs.value.find(job => ['PENDING', 'RUNNING'].includes(job.status)); if (active) { currentJob.value = active; pollTimer = setInterval(() => { void pollJob(active.id) }, 1500) } } } catch (error) { ElMessage.error(errorMessage(error)) } })
onUnmounted(() => { if (pollTimer) clearInterval(pollTimer) })
</script>

<template>
  <div class="page-heading"><div><p class="eyebrow">CONNECTOR DETAIL</p><h1>{{ connector?.name || '连接器' }}</h1><p class="muted">{{ connector?.type }} · {{ connector?.base_url || '无远程地址' }}</p></div><RouterLink to="/connectors"><el-button>返回列表</el-button></RouterLink></div>
  <div v-if="connector" class="panel"><div class="actions"><el-button v-if="connector.type === 'rest'" :loading="busy" @click="run(testConnection, '连接成功')">测试连接</el-button><el-button v-if="connector.type === 'rest' || connector.type === 'file'" :loading="busy" @click="run(fetchSample, '样例已加载')">获取样例</el-button><RouterLink :to="`/connectors/${id}/mapping`"><el-button type="primary" plain>配置字段映射</el-button></RouterLink><el-button v-if="connector.type === 'rest'" type="primary" :loading="busy" :disabled="currentJob?.status === 'PENDING' || currentJob?.status === 'RUNNING'" @click="startJob">同步数据</el-button><el-button v-if="connector.type === 'file'" type="primary" :loading="busy" @click="run(importData, '导入完成')">上传并导入</el-button></div>
    <p v-if="connectionTest" class="muted">连接成功 · HTTP {{ connectionTest.status_code }} · {{ connectionTest.latency_ms }} ms · {{ connectionTest.content_type }}</p>
    <div v-if="connector.type === 'rest'" class="input-section"><strong>同步配置</strong><p>方法 {{ connector.config.method || 'GET' }} · 模式 {{ connector.config.sync_mode || 'FULL' }} · 分页 {{ (connector.config.pagination as Record<string, unknown> | undefined)?.type || 'NONE' }} · 最近游标 {{ connector.config.last_sync_value || '—' }}</p><p>认证 {{ connector.auth_type }} · 凭据{{ connector.credential_configured ? '已配置' : '未配置' }}</p></div>
    <div class="input-section"><strong>数据能力</strong><p>读取：{{ connector.capabilities.read.join('、') || '无' }} · 写入：{{ connector.capabilities.write.join('、') || '无' }}</p></div>
    <div v-if="connector.type === 'file'" class="input-section"><label>选择 JSON、CSV 或 XLSX 文件</label><input type="file" accept=".json,.csv,.xlsx" @change="chooseFile" /></div>
    <div v-if="connector.type !== 'rest'" class="input-section"><label>或粘贴 JSON 数组直接导入</label><el-input v-model="jsonInput" type="textarea" :rows="5" placeholder='[{"waybillNo":"YD001"}]' /><el-button style="margin-top:10px" :loading="busy" @click="run(importPasted, '导入完成')">导入 JSON</el-button></div>
    <div v-if="connector.type === 'webhook'" class="input-section"><strong>Webhook 地址</strong><p><code>/api/v1/webhooks/{{ id }}</code></p><p class="muted">请求头使用 X-Webhook-Secret，正文为 JSON 对象或数组。</p></div>
    <div v-if="fields.length" class="input-section"><strong>检测到的字段</strong><p>{{ fields.join('、') }}</p><pre>{{ JSON.stringify(sample, null, 2) }}</pre></div>
    <div v-if="result" class="input-section"><strong>导入结果</strong><p>读取 {{ result.total }} 条 · 成功 {{ result.success }} · 失败 {{ result.failed }}</p><p>新增运单 {{ result.imported }} · 更新运单 {{ result.updated }} · 新增司机 {{ result.drivers_created }} · 新增车辆 {{ result.vehicles_created }} · 新增线路 {{ result.routes_created }} · 新增轨迹 {{ result.tracking_events_created }}</p><p v-for="line in result.warnings" :key="line" class="muted">⚠ {{ line }}</p><p v-for="line in result.errors" :key="line" class="error">{{ line }}</p></div>
    <div v-if="connector.type === 'rest'" class="input-section"><strong>同步历史</strong><el-table :data="jobs" stripe><el-table-column label="创建时间" min-width="170"><template #default="scope">{{ formatDateTime(scope.row.created_at) }}</template></el-table-column><el-table-column prop="status" label="状态" width="160" /><el-table-column prop="total_count" label="读取" width="80" /><el-table-column prop="success_count" label="成功" width="80" /><el-table-column prop="failed_count" label="失败" width="80" /><el-table-column label="详情" width="90"><template #default="scope"><el-button text @click="selectJob(scope.row.id)">查看</el-button></template></el-table-column></el-table></div>
    <div v-if="currentJob" class="input-section"><strong>作业 {{ currentJob.status }}</strong><p v-if="currentJob.error_message" class="error">{{ currentJob.error_message }}</p><p>读取 {{ currentJob.total_count }} · 成功 {{ currentJob.success_count }} · 失败 {{ currentJob.failed_count }} · 新增 {{ currentJob.result.imported ?? 0 }} · 更新 {{ currentJob.result.updated ?? 0 }}</p><div v-for="issue in issues" :key="issue.id"><el-tag :type="issue.level === 'FATAL' || issue.level === 'ERROR' ? 'danger' : 'warning'">{{ issue.level }}</el-tag> 第 {{ issue.row_number || '—' }} 条 · {{ issue.code }}：{{ issue.message }}</div></div>
  </div>
</template>
