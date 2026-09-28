<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { init, use, type EChartsType } from 'echarts/core'
import { BarChart, LineChart, PieChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { ElMessage } from 'element-plus'
import { platform, type AIUsageDashboard } from '../api/platform'
import { formatDateTime } from '../utils/datetime'
import { errorMessage } from '../utils/errors'

use([LineChart, BarChart, PieChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer])

const loading = ref(true)
const data = ref<AIUsageDashboard | null>(null)
const error = ref('')

const trendEl = ref<HTMLElement | null>(null)
const purposeEl = ref<HTMLElement | null>(null)
const modelEl = ref<HTMLElement | null>(null)

let charts: EChartsType[] = []
let observers: ResizeObserver[] = []

function watchSize(element: HTMLElement, chart: EChartsType) {
  const observer = new ResizeObserver(() => chart.resize())
  observer.observe(element)
  observers.push(observer)
  charts.push(chart)
}

function cleanupCharts() {
  observers.forEach(item => item.disconnect())
  charts.forEach(item => item.dispose())
  observers = []
  charts = []
}

onUnmounted(cleanupCharts)

function formatPurpose(purpose: string): string {
  const mapping: Record<string, string> = {
    chat: '智能问答助手',
    exception_analysis: '异常智能分析',
    dashboard_summary: '运营看板摘要',
    dashboard: '运营看板摘要',
    decision: '智能决策路由',
  }
  return mapping[purpose] || purpose
}

function purposeTagType(purpose: string): '' | 'success' | 'warning' | 'info' {
  if (purpose === 'chat') return 'success'
  if (purpose === 'exception_analysis') return 'warning'
  if (purpose === 'dashboard_summary' || purpose === 'dashboard') return ''
  return 'info'
}

function formatCost(cost: number | string | undefined | null): string {
  const val = Number(cost || 0)
  if (val === 0) return '¥0.0000'
  if (val < 0.0001) return '< ¥0.0001'
  return `¥${val.toFixed(4)}`
}

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const res = await platform.aiUsageDashboard()
    data.value = res
    cleanupCharts()

    // 1. 趋势图 (Tokens 与 调用次数)
    if (trendEl.value && res.trend.length) {
      const chart = init(trendEl.value)
      chart.setOption({
        tooltip: {
          trigger: 'axis',
          axisPointer: { type: 'cross', crossStyle: { color: '#94a3b8' } },
        },
        legend: { data: ['Token 消耗', '调用次数'], bottom: 0, textStyle: { fontSize: 12, color: '#475569' } },
        grid: { left: 55, right: 45, top: 32, bottom: 40 },
        xAxis: {
          type: 'category',
          data: res.trend.map(item => item.date.slice(5)),
          axisLine: { lineStyle: { color: '#cbd5e1' } },
          axisLabel: { color: '#64748b' },
        },
        yAxis: [
          {
            type: 'value',
            name: 'Tokens',
            minInterval: 1,
            nameTextStyle: { color: '#64748b' },
            splitLine: { lineStyle: { color: '#f1f5f9' } },
          },
          {
            type: 'value',
            name: '调用次数',
            minInterval: 1,
            nameTextStyle: { color: '#64748b' },
            splitLine: { show: false },
          },
        ],
        series: [
          {
            name: 'Token 消耗',
            type: 'line',
            smooth: true,
            symbol: 'circle',
            symbolSize: 6,
            itemStyle: { color: '#3b82f6' },
            lineStyle: { width: 3, color: '#3b82f6' },
            areaStyle: {
              color: {
                type: 'linear',
                x: 0,
                y: 0,
                x2: 0,
                y2: 1,
                colorStops: [
                  { offset: 0, color: 'rgba(59, 130, 246, 0.28)' },
                  { offset: 1, color: 'rgba(59, 130, 246, 0.02)' },
                ],
              },
            },
            data: res.trend.map(item => item.tokens),
          },
          {
            name: '调用次数',
            type: 'bar',
            yAxisIndex: 1,
            barWidth: '28%',
            itemStyle: {
              color: '#10b981',
              borderRadius: [4, 4, 0, 0],
            },
            data: res.trend.map(item => item.calls),
          },
        ],
      })
      watchSize(trendEl.value, chart)
    }

    // 2. 目的分布环形图
    if (purposeEl.value && res.distribution_by_purpose.length) {
      const chart = init(purposeEl.value)
      chart.setOption({
        tooltip: { trigger: 'item', formatter: '{b}<br/><b>{c}</b> 次 ({d}%)' },
        legend: { bottom: 0, textStyle: { fontSize: 12, color: '#475569' } },
        color: ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899'],
        series: [{
          type: 'pie',
          radius: ['45%', '70%'],
          center: ['50%', '45%'],
          avoidLabelOverlap: false,
          itemStyle: {
            borderRadius: 6,
            borderColor: '#fff',
            borderWidth: 2,
          },
          data: res.distribution_by_purpose.map(item => ({
            name: formatPurpose(item.purpose),
            value: item.calls,
          })),
        }],
      })
      watchSize(purposeEl.value, chart)
    }

    // 3. 模型分布柱图
    if (modelEl.value && res.distribution_by_model.length) {
      const chart = init(modelEl.value)
      chart.setOption({
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
        grid: { left: 55, right: 25, top: 25, bottom: 35 },
        xAxis: {
          type: 'category',
          data: res.distribution_by_model.map(item => item.model || '未标识'),
          axisLine: { lineStyle: { color: '#cbd5e1' } },
        },
        yAxis: {
          type: 'value',
          name: 'Token 数',
          minInterval: 1,
          splitLine: { lineStyle: { color: '#f1f5f9' } },
        },
        series: [{
          type: 'bar',
          barWidth: '32%',
          itemStyle: {
            color: '#8b5cf6',
            borderRadius: [4, 4, 0, 0],
          },
          data: res.distribution_by_model.map(item => item.tokens),
        }],
      })
      watchSize(modelEl.value, chart)
    }
  } catch (err) {
    error.value = '无法加载 AI 用量监控数据。'
    ElMessage.error(errorMessage(err))
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>

<template>
  <div class="ai-usage-page">
    <div class="page-heading">
      <div>
        <div class="heading-tag-line">
          <span class="eyebrow">AI TELEMETRY & GOVERNANCE</span>
          <span class="rate-badge">当前定价：输入 ¥0.8 / 百万 Tokens · 输出 ¥2.7 / 百万 Tokens</span>
        </div>
        <h1>AI 用量与运行监控</h1>
        <p class="muted">全景监控大模型推理调用、Token 消耗、精确计费与主备高可用容灾状态</p>
      </div>
      <el-button type="primary" plain :loading="loading" @click="loadData">
        <span style="margin-right: 4px;">↻</span> 刷新数据
      </el-button>
    </div>

    <el-alert v-if="error" :title="error" type="error" show-icon style="margin-bottom: 16px" />

    <div v-loading="loading" class="dashboard">
      <!-- 模型网关主备状态面板 -->
      <div class="gateway-grid">
        <div class="gateway-card primary-card">
          <div class="gateway-header">
            <div class="title-with-status">
              <span class="status-indicator active"></span>
              <strong>主模型网关（Primary）</strong>
            </div>
            <el-tag :type="data?.models_info.primary.configured ? 'success' : 'info'" effect="light" size="small">
              {{ data?.models_info.primary.configured ? '在线 · 优先请求' : '未就绪' }}
            </el-tag>
          </div>
          <div class="gateway-body">
            <div class="gateway-item">
              <span class="item-label">协议/提供者:</span>
              <span class="item-value">{{ data?.models_info.primary.provider }}</span>
            </div>
            <div class="gateway-item">
              <span class="item-label">模型标识:</span>
              <span class="item-value"><code class="model-code">{{ data?.models_info.primary.model }}</code></span>
            </div>
            <div class="gateway-item">
              <span class="item-label">服务地址:</span>
              <span class="item-value endpoint">{{ data?.models_info.primary.base_url }}</span>
            </div>
          </div>
          <div class="gateway-footer">
            <span>内网专线节点 (192.168.2.133)，低时延首选通道</span>
          </div>
        </div>

        <div class="gateway-card fallback-card">
          <div class="gateway-header">
            <div class="title-with-status">
              <span class="status-indicator fallback"></span>
              <strong>容灾备份模型（Fallback）</strong>
            </div>
            <el-tag :type="data?.models_info.fallback.configured ? 'warning' : 'info'" effect="light" size="small">
              {{ data?.models_info.fallback.configured ? '备用就绪 · 自动降级' : '未就绪' }}
            </el-tag>
          </div>
          <div class="gateway-body">
            <div class="gateway-item">
              <span class="item-label">协议/提供者:</span>
              <span class="item-value">{{ data?.models_info.fallback.provider }} (官网 DashScope)</span>
            </div>
            <div class="gateway-item">
              <span class="item-label">模型标识:</span>
              <span class="item-value"><code class="model-code">{{ data?.models_info.fallback.model }}</code></span>
            </div>
            <div class="gateway-item">
              <span class="item-label">服务地址:</span>
              <span class="item-value endpoint">{{ data?.models_info.fallback.base_url }}</span>
            </div>
          </div>
          <div class="gateway-footer">
            <span>当主网关出现超时、连通性故障或 5xx 错误时，毫秒级无感接管</span>
          </div>
        </div>
      </div>

      <!-- 核心指标卡片 -->
      <div class="metric-grid">
        <div class="metric-card">
          <span class="metric-label">今日 Token 消耗</span>
          <strong class="metric-val">{{ (data?.summary.today_tokens || 0).toLocaleString() }}</strong>
          <small class="metric-sub">
            <span class="token-in">入: {{ (data?.summary.today_input_tokens || 0).toLocaleString() }}</span>
            <span class="divider">/</span>
            <span class="token-out">出: {{ (data?.summary.today_output_tokens || 0).toLocaleString() }}</span>
          </small>
        </div>
        <div class="metric-card">
          <span class="metric-label">累计 Token 总量</span>
          <strong class="metric-val">{{ (data?.summary.total_tokens || 0).toLocaleString() }}</strong>
          <small class="metric-sub">
            <span class="token-in">入: {{ (data?.summary.total_input_tokens || 0).toLocaleString() }}</span>
            <span class="divider">/</span>
            <span class="token-out">出: {{ (data?.summary.total_output_tokens || 0).toLocaleString() }}</span>
          </small>
        </div>
        <div class="metric-card">
          <span class="metric-label">累计调用次数</span>
          <strong class="metric-val">{{ (data?.summary.total_calls || 0).toLocaleString() }} <span class="unit">次</span></strong>
          <small class="metric-sub">今日调用: {{ data?.summary.today_calls || 0 }} 次</small>
        </div>
        <div class="metric-card cost-card">
          <span class="metric-label">累计推理成本</span>
          <strong class="metric-val cost-val">¥{{ (data?.summary.total_cost || 0).toFixed(4) }}</strong>
          <small class="metric-sub">今日成本: ¥{{ (data?.summary.today_cost || 0).toFixed(4) }}</small>
        </div>
      </div>

      <!-- 图表渲染区域 -->
      <div class="chart-grid">
        <section class="panel chart-panel">
          <div class="panel-header">
            <div class="panel-title">近 7 日 Token 消耗与调用量趋势</div>
            <span class="panel-extra">双轴统计</span>
          </div>
          <div ref="trendEl" class="chart" style="height: 290px;"></div>
        </section>
        <section class="panel chart-panel">
          <div class="panel-header">
            <div class="panel-title">AI 调用业务场景分布</div>
            <span class="panel-extra">业务模块占比</span>
          </div>
          <div ref="purposeEl" class="chart" style="height: 290px;"></div>
        </section>
      </div>

      <div class="chart-grid" style="margin-top: 16px;">
        <section class="panel chart-panel">
          <div class="panel-header">
            <div class="panel-title">各模型 Token 用量对比</div>
            <span class="panel-extra">负载分布</span>
          </div>
          <div ref="modelEl" class="chart" style="height: 250px;"></div>
        </section>
        <section class="panel rule-panel">
          <div class="panel-header">
            <div class="panel-title">AI 治理与高可用保障机制</div>
          </div>
          <div class="rule-content">
            <div class="rule-item">
              <span class="rule-icon">🛡️</span>
              <div>
                <strong>自动主备降级</strong>
                <p>请求优先调度至内网高性能算力节点；若遇网络抖动或服务故障，客户端无感知自动切换至阿里云 DashScope 官网 Qwen 算力，确保业务 99.9% 连续性。</p>
              </div>
            </div>
            <div class="rule-item">
              <span class="rule-icon">🔒</span>
              <div>
                <strong>防幻觉隔离与可追溯</strong>
                <p>大模型仅参与分析推理，严禁生成并直行非受控 SQL。所有调用的 Prompt、Completion、Token 用量与耗时均记录于本地审计日志，多租户逻辑严格隔离。</p>
              </div>
            </div>
            <div class="rule-item">
              <span class="rule-icon">💰</span>
              <div>
                <strong>精细化计费管控</strong>
                <p>以标准百万 Token 费率（输入 ¥0.8 / 输出 ¥2.7）为基准，实时拆分计算 Prompt 与 Completion 成本，杜绝隐形算力超支。</p>
              </div>
            </div>
          </div>
        </section>
      </div>

      <!-- 最近调用明细表格 -->
      <section class="panel table-panel" style="margin-top: 20px;">
        <div class="panel-header">
          <div class="panel-title">最近 AI 调用审计明细</div>
          <span class="panel-extra">最近 {{ data?.recent_logs.length || 0 }} 次请求追溯</span>
        </div>
        <el-table :data="data?.recent_logs || []" stripe style="width: 100%;" :header-cell-style="{ background: '#f8fafc', color: '#475569', fontWeight: 600 }">
          <el-table-column label="调用时间" min-width="170">
            <template #default="scope">
              <span class="time-col">{{ formatDateTime(scope.row.created_at) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="业务场景" width="150">
            <template #default="scope">
              <el-tag :type="purposeTagType(scope.row.purpose)" size="small">
                {{ formatPurpose(scope.row.purpose) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="provider" label="网关提供者" width="150">
            <template #default="scope">
              <span class="provider-col">{{ scope.row.provider }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="model" label="实际使用模型" min-width="160">
            <template #default="scope">
              <code class="model-inline-code">{{ scope.row.model || '—' }}</code>
            </template>
          </el-table-column>
          <el-table-column label="输入 Token" width="120" align="right">
            <template #default="scope">
              <span class="num-col in">{{ scope.row.input_tokens.toLocaleString() }}</span>
            </template>
          </el-table-column>
          <el-table-column label="输出 Token" width="120" align="right">
            <template #default="scope">
              <span class="num-col out">{{ scope.row.output_tokens.toLocaleString() }}</span>
            </template>
          </el-table-column>
          <el-table-column label="总消耗" width="130" align="right">
            <template #default="scope">
              <strong class="num-col total">{{ (scope.row.input_tokens + scope.row.output_tokens).toLocaleString() }}</strong>
            </template>
          </el-table-column>
          <el-table-column label="单次成本" width="110" align="right">
            <template #default="scope">
              <span class="cost-col">{{ formatCost(scope.row.cost) }}</span>
            </template>
          </el-table-column>
        </el-table>
        <p v-if="!data?.recent_logs.length" class="muted" style="text-align: center; padding: 28px 0;">暂无 AI 调用记录</p>
      </section>
    </div>
  </div>
</template>

<style scoped>
.ai-usage-page {
  animation: fadeIn 0.25s ease-in-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

.heading-tag-line {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 4px;
}

.rate-badge {
  font-size: 11px;
  padding: 2px 8px;
  background-color: #f1f5f9;
  color: #475569;
  border-radius: 4px;
  border: 1px solid #e2e8f0;
}

.gateway-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

.gateway-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 16px 18px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.primary-card {
  border-left: 4px solid #3b82f6;
}

.fallback-card {
  border-left: 4px solid #f59e0b;
}

.gateway-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #f1f5f9;
}

.title-with-status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  color: #1e293b;
}

.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}

.status-indicator.active {
  background-color: #10b981;
  box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.2);
}

.status-indicator.fallback {
  background-color: #f59e0b;
  box-shadow: 0 0 0 3px rgba(245, 158, 11, 0.2);
}

.gateway-body {
  font-size: 13px;
  color: #334155;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.gateway-item {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.item-label {
  color: #64748b;
  min-width: 75px;
}

.item-value {
  font-weight: 500;
}

.item-value.endpoint {
  font-size: 12px;
  color: #475569;
  word-break: break-all;
}

.model-code {
  background: #f8fafc;
  color: #0f172a;
  padding: 1px 6px;
  border-radius: 4px;
  border: 1px solid #e2e8f0;
  font-size: 12px;
}

.gateway-footer {
  margin-top: 12px;
  padding-top: 8px;
  border-top: 1px dashed #f1f5f9;
  font-size: 12px;
  color: #64748b;
}

.metric-val {
  font-size: 24px;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.5px;
}

.metric-val .unit {
  font-size: 13px;
  font-weight: normal;
  color: #64748b;
}

.cost-card {
  border-left: 3px solid #10b981;
}

.cost-val {
  color: #047857;
}

.metric-sub {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #64748b;
  margin-top: 4px;
}

.token-in {
  color: #2563eb;
}

.token-out {
  color: #059669;
}

.divider {
  color: #cbd5e1;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}

.panel-title {
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
}

.panel-extra {
  font-size: 12px;
  color: #94a3b8;
}

.chart-panel {
  padding: 18px 20px;
}

.rule-panel {
  padding: 18px 20px;
}

.rule-content {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-top: 8px;
}

.rule-item {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.rule-icon {
  font-size: 18px;
  line-height: 1.2;
}

.rule-item strong {
  font-size: 13px;
  color: #1e293b;
  display: block;
  margin-bottom: 2px;
}

.rule-item p {
  margin: 0;
  font-size: 12px;
  line-height: 1.6;
  color: #64748b;
}

.table-panel {
  padding: 18px 20px;
}

.time-col {
  font-size: 12px;
  color: #334155;
}

.provider-col {
  font-size: 12px;
  color: #64748b;
}

.model-inline-code {
  font-size: 12px;
  color: #2563eb;
  background: #eff6ff;
  padding: 2px 6px;
  border-radius: 4px;
}

.num-col {
  font-size: 13px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.num-col.in {
  color: #2563eb;
}

.num-col.out {
  color: #059669;
}

.num-col.total {
  color: #0f172a;
}

.cost-col {
  font-size: 13px;
  font-weight: 600;
  color: #047857;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}
</style>
