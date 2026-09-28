<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { platform, type LogisticsException } from '../api/platform'
import { errorMessage } from '../utils/errors'
import { formatDateTime } from '../utils/datetime'

const id = String(useRoute().params.id)
const detail = ref<LogisticsException | null>(null)
const busy = ref(false)
async function load() { try { detail.value = await platform.exception(id) } catch (error) { ElMessage.error(errorMessage(error)) } }
async function resolve() { busy.value = true; try { detail.value = await platform.resolveException(id); ElMessage.success('异常已解决') } catch (error) { ElMessage.error(errorMessage(error)) } finally { busy.value = false } }
async function analyze() { busy.value = true; try { detail.value = await platform.analyzeException(id); ElMessage.success('分析已更新') } catch (error) { ElMessage.error(errorMessage(error)) } finally { busy.value = false } }
onMounted(load)
</script>

<template>
  <div class="page-heading"><div><p class="eyebrow">EXCEPTION DETAIL</p><h1>{{ detail?.type || '异常详情' }}</h1><p class="muted">{{ formatDateTime(detail?.detected_at) }}</p></div><RouterLink to="/exceptions"><el-button>返回列表</el-button></RouterLink></div>
  <template v-if="detail"><div class="panel"><el-descriptions :column="2" border><el-descriptions-item label="风险等级">{{ detail.level }}</el-descriptions-item><el-descriptions-item label="状态">{{ detail.status }}</el-descriptions-item><el-descriptions-item label="规则">{{ detail.type }}</el-descriptions-item><el-descriptions-item label="关联运单"><RouterLink :to="`/shipments/${detail.shipment_id}`" class="table-link">查看运单</RouterLink></el-descriptions-item></el-descriptions><div class="detail-section"><h3>触发原因</h3><p>{{ detail.reason }}</p></div><div class="detail-section"><h3>分析</h3><p>{{ detail.ai_analysis || '尚未生成分析。可先参考规则建议。' }}</p><p v-if="detail.ai_analysis?.startsWith('规则分析')" class="form-hint">当前为规则分析。配置 LLM 后可生成模型分析。</p></div><div class="detail-section"><h3>建议动作</h3><p>{{ detail.suggestion || '暂无建议' }}</p></div><div class="actions"><el-button :loading="busy" @click="analyze">更新分析</el-button><el-button v-if="detail.status === 'open'" type="primary" :loading="busy" @click="resolve">标记为已解决</el-button></div></div></template>
</template>
