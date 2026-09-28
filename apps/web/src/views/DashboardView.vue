<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { init, use, type EChartsType } from 'echarts/core'
import { LineChart, PieChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { platform, type LogisticsException } from '../api/platform'

const router = useRouter()
const loading = ref(true)
const overview = ref({ shipments_today: 0, in_transit: 0, exception_count: 0, high_risk_count: 0, type_distribution: [] as {type: string; count: number}[], recent_exceptions: [] as LogisticsException[] })
const ranking = ref<{route_name: string; exception_count: number}[]>([])
const summary = ref('')
const summaryProvider = ref('rules')
const trendEl = ref<HTMLElement | null>(null)
const typeEl = ref<HTMLElement | null>(null)
const error = ref('')
use([LineChart, PieChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer])
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

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const [data, trend, routes, ai] = await Promise.all([
      platform.overview(),
      platform.trend(),
      platform.routeRanking(),
      platform.summary(),
    ])
    overview.value = data
    ranking.value = routes
    summary.value = ai.summary
    summaryProvider.value = ai.provider

    cleanupCharts()

    if (trendEl.value) {
      const chart = init(trendEl.value)
      chart.setOption({
        tooltip: { trigger: 'axis' },
        grid: { left: 40, right: 18, top: 22, bottom: 30 },
        xAxis: { type: 'category', data: trend.map(item => item.date.slice(5)) },
        yAxis: { type: 'value', minInterval: 1 },
        series: [{
          type: 'line',
          smooth: true,
          areaStyle: { color: '#d9ebfb' },
          lineStyle: { color: '#1978ba', width: 3 },
          itemStyle: { color: '#1978ba' },
          data: trend.map(item => item.count),
        }],
      })
      watchSize(trendEl.value, chart)
    }
    if (typeEl.value) {
      const chart = init(typeEl.value)
      chart.setOption({
        tooltip: { trigger: 'item' },
        legend: { bottom: 0 },
        series: [{
          type: 'pie',
          radius: ['48%', '72%'],
          data: data.type_distribution.map(item => ({ name: item.type, value: item.count })),
        }],
      })
      watchSize(typeEl.value, chart)
    }
  } catch {
    error.value = '无法加载仪表盘数据。'
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>

<template>
  <div class="page-heading">
    <div>
      <p class="eyebrow">OPERATIONS OVERVIEW</p>
      <h1>物流运行概览</h1>
      <p class="muted">实时查看运单与异常处理情况</p>
    </div>
    <el-button :loading="loading" @click="loadData">刷新数据</el-button>
  </div>
  <el-alert v-if="error" :title="error" type="error" show-icon style="margin-bottom: 16px" />
  <div v-loading="loading" class="dashboard">
    <div class="metric-grid">
      <div class="metric-card" style="cursor: pointer" @click="router.push('/shipments')">
        <span>今日运单</span>
        <strong>{{ overview.shipments_today }}</strong>
        <small>今日新增 · 点击查看</small>
      </div>
      <div class="metric-card" style="cursor: pointer" @click="router.push('/shipments')">
        <span>在途运单</span>
        <strong>{{ overview.in_transit }}</strong>
        <small>当前运输中 · 点击查看</small>
      </div>
      <div class="metric-card" style="cursor: pointer" @click="router.push('/exceptions')">
        <span>待处理异常</span>
        <strong>{{ overview.exception_count }}</strong>
        <small>需要关注 · 点击查看</small>
      </div>
      <div class="metric-card risk" style="cursor: pointer" @click="router.push('/exceptions')">
        <span>高风险异常</span>
        <strong>{{ overview.high_risk_count }}</strong>
        <small>优先处理 · 点击查看</small>
      </div>
    </div>
    <div class="panel ai-summary">
      <div class="panel-title">
        ✧ 每日运营摘要
        <small class="muted">{{ summaryProvider === 'rules' ? '规则统计' : '模型分析' }}</small>
      </div>
      <p>{{ summary }}</p>
    </div>
    <div class="chart-grid">
      <section class="panel">
        <div class="panel-title">近 7 日异常趋势</div>
        <div ref="trendEl" class="chart"></div>
      </section>
      <section class="panel">
        <div class="panel-title">异常类型分布</div>
        <div ref="typeEl" class="chart"></div>
      </section>
    </div>
    <div class="chart-grid">
      <section class="panel">
        <div class="panel-title">线路异常排行</div>
        <div v-for="(item, index) in ranking" :key="item.route_name" class="ranking-row">
          <span>{{ index + 1 }}. {{ item.route_name }}</span>
          <b>{{ item.exception_count }}</b>
        </div>
        <p v-if="!ranking.length" class="muted">暂无线路异常</p>
      </section>
      <section class="panel">
        <div class="panel-title">最近异常</div>
        <RouterLink v-for="item in overview.recent_exceptions" :key="item.id" :to="`/exceptions/${item.id}`" class="recent-row">
          <span>{{ item.type }}</span>
          <el-tag :type="item.level === 'CRITICAL' || item.level === 'HIGH' ? 'danger' : 'warning'" size="small">{{ item.level }}</el-tag>
        </RouterLink>
        <p v-if="!overview.recent_exceptions.length" class="muted">暂无异常</p>
      </section>
    </div>
  </div>
</template>
