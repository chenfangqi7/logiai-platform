<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { platform, type Connector, type ImportResult } from '../api/platform'
import { errorMessage } from '../utils/errors'

const route = useRoute()
const id = String(route.params.id)
const connector = ref<Connector | null>(null)
const sample = ref<Record<string, unknown>[]>([])
const fields = ref<string[]>([])
const file = ref<File | null>(null)
const jsonInput = ref('')
const result = ref<ImportResult | null>(null)
const busy = ref(false)
function chooseFile(event: Event) { file.value = (event.target as HTMLInputElement).files?.[0] || null }
async function run(action: () => Promise<unknown>, success: string) { busy.value = true; try { await action(); ElMessage.success(success) } catch (error) { ElMessage.error(errorMessage(error)) } finally { busy.value = false } }
async function fetchSample() { if (!connector.value) return; const data = connector.value.type === 'file' && file.value ? await platform.fileSample(id, file.value) : await platform.sampleConnector(id); sample.value = data.rows; fields.value = data.fields; sessionStorage.setItem(`sample_${id}`, JSON.stringify(data)) }
async function importData() { if (!connector.value) return; if (connector.value.type === 'rest') result.value = await platform.syncConnector(id); else if (file.value) result.value = await platform.uploadConnector(id, file.value); else { const parsed: unknown = JSON.parse(jsonInput.value); if (!Array.isArray(parsed)) throw new Error('请输入 JSON 数组'); result.value = await platform.importJson(id, parsed as Record<string, unknown>[]) } }
async function importPasted() { const parsed: unknown = JSON.parse(jsonInput.value); if (!Array.isArray(parsed)) throw new Error('请输入 JSON 数组'); result.value = await platform.importJson(id, parsed as Record<string, unknown>[]) }
onMounted(async () => { try { connector.value = await platform.connector(id) } catch (error) { ElMessage.error(errorMessage(error)) } })
</script>

<template>
  <div class="page-heading"><div><p class="eyebrow">CONNECTOR DETAIL</p><h1>{{ connector?.name || '连接器' }}</h1><p class="muted">{{ connector?.type }} · {{ connector?.base_url || '无远程地址' }}</p></div><RouterLink to="/connectors"><el-button>返回列表</el-button></RouterLink></div>
  <div v-if="connector" class="panel"><div class="actions"><el-button v-if="connector.type === 'rest'" :loading="busy" @click="run(() => platform.testConnector(id), '连接成功')">测试连接</el-button><el-button v-if="connector.type === 'rest' || connector.type === 'file'" :loading="busy" @click="run(fetchSample, '样例已加载')">获取样例</el-button><RouterLink :to="`/connectors/${id}/mapping`"><el-button type="primary" plain>配置字段映射</el-button></RouterLink><el-button v-if="connector.type === 'rest' || connector.type === 'file'" type="primary" :loading="busy" @click="run(importData, '导入完成')">{{ connector.type === 'rest' ? '同步数据' : '上传并导入' }}</el-button></div>
    <div v-if="connector.type === 'file'" class="input-section"><label>选择 JSON、CSV 或 XLSX 文件</label><input type="file" accept=".json,.csv,.xlsx" @change="chooseFile" /></div>
    <div v-if="connector.type !== 'rest'" class="input-section"><label>或粘贴 JSON 数组直接导入</label><el-input v-model="jsonInput" type="textarea" :rows="5" placeholder='[{"waybillNo":"YD001"}]' /><el-button style="margin-top:10px" :loading="busy" @click="run(importPasted, '导入完成')">导入 JSON</el-button></div>
    <div v-if="connector.type === 'webhook'" class="input-section"><strong>Webhook 地址</strong><p><code>/api/v1/webhooks/{{ id }}</code></p><p class="muted">请求头使用 X-Webhook-Secret，正文为 JSON 对象或数组。</p></div>
    <div v-if="fields.length" class="input-section"><strong>检测到的字段</strong><p>{{ fields.join('、') }}</p><pre>{{ JSON.stringify(sample, null, 2) }}</pre></div>
    <div v-if="result" class="input-section"><strong>导入结果</strong><p>新增 {{ result.imported }} · 更新 {{ result.updated }} · 拒绝 {{ result.rejected }}</p><p v-for="line in result.errors" :key="line" class="error">{{ line }}</p></div>
  </div>
</template>
