<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { platform } from '../api/platform'
import { errorMessage } from '../utils/errors'

const router = useRouter()
const saving = ref(false)
const form = reactive({ name: '演示 TMS 接口', type: 'rest', base_url: 'http://server:8000/demo/tms/shipments', auth_type: 'none',
  items_path: '', method: 'GET', timeout_seconds: 10, queryRows: [] as {key:string; value:string}[], bodyText: '{}',
  paginationType: 'NONE', paginationLocation: 'query', pageSize: 100, maxPages: 20, pageParam: 'page', sizeParam: 'pageSize',
  offsetParam: 'offset', cursorParam: 'cursor', cursorPath: 'nextCursor', totalPath: '',
  syncMode: 'FULL', incrementalField: '', incrementalParam: '', incrementalLocation: 'query',
  token: '', username: '', password: '', header_name: '', header_value: '', customHeaders: [] as {key:string; value:string}[], webhook_secret: '' })
async function submit() {
  saving.value = true
  try {
    const config: Record<string, unknown> = {}
    for (const key of ['items_path', 'token', 'username', 'password', 'header_name', 'header_value', 'webhook_secret'] as const) if (form[key]) config[key] = form[key]
    if (form.type === 'rest') {
      config.method = form.method; config.timeout_seconds = form.timeout_seconds
      config.query_params = Object.fromEntries(form.queryRows.filter(row => row.key).map(row => [row.key, row.value]))
      const body: unknown = JSON.parse(form.bodyText || '{}'); if (!body || typeof body !== 'object' || Array.isArray(body)) throw new Error('请求体必须是 JSON 对象')
      config.request_body = body
      if (form.auth_type === 'custom_headers') config.headers = Object.fromEntries(form.customHeaders.filter(row => row.key).map(row => [row.key, row.value]))
      if (form.paginationType !== 'NONE') config.pagination = {type:form.paginationType, location:form.paginationLocation, page_size:form.pageSize, max_pages:form.maxPages,
        page_param:form.pageParam, size_param:form.sizeParam, offset_param:form.offsetParam, cursor_param:form.cursorParam, cursor_path:form.cursorPath,
        ...(form.totalPath ? {total_path:form.totalPath} : {})}
      config.sync_mode = form.syncMode
      if (form.syncMode === 'INCREMENTAL') { config.incremental_field = form.incrementalField; config.incremental_param = form.incrementalParam || form.incrementalField; config.incremental_location = form.incrementalLocation }
    }
    const item = await platform.createConnector({name: form.name, type: form.type, base_url: form.type === 'rest' ? form.base_url : null, auth_type: form.type === 'rest' ? form.auth_type : 'none', config})
    ElMessage.success('连接器已创建'); await router.push(`/connectors/${item.id}`)
  } catch (error) { ElMessage.error(errorMessage(error)) } finally { saving.value = false }
}
</script>

<template>
  <div class="page-heading"><div><p class="eyebrow">NEW CONNECTOR</p><h1>新建连接器</h1></div><RouterLink to="/connectors"><el-button>返回列表</el-button></RouterLink></div>
  <div class="panel form-panel"><el-form :model="form" label-position="top">
    <el-form-item label="连接器名称"><el-input v-model="form.name" /></el-form-item>
    <el-form-item label="类型"><el-select v-model="form.type" style="width:100%"><el-option label="REST API" value="rest" /><el-option label="Webhook" value="webhook" /><el-option label="JSON / CSV / Excel 文件" value="file" /></el-select></el-form-item>
    <template v-if="form.type === 'rest'"><el-form-item label="接口 URL"><el-input v-model="form.base_url" /></el-form-item><p class="form-hint">Docker 容器环境填写：<code>http://server:8000/demo/tms/shipments</code>；宿主机非容器运行填写：<code>http://localhost:8001/demo/tms/shipments</code>。</p>
      <el-form-item label="请求方法"><el-select v-model="form.method" style="width:100%"><el-option label="GET" value="GET" /><el-option label="POST" value="POST" /></el-select></el-form-item>
      <el-form-item label="超时（秒）"><el-input-number v-model="form.timeout_seconds" :min="1" :max="30" /></el-form-item>
      <el-form-item label="数据列表路径（可选）"><el-input v-model="form.items_path" placeholder="例如 data.items" /></el-form-item>
      <el-form-item label="Query 参数"><div style="width:100%"><div v-for="(row,index) in form.queryRows" :key="index" style="display:flex;gap:8px;margin-bottom:8px"><el-input v-model="row.key" placeholder="参数名" /><el-input v-model="row.value" placeholder="参数值" /><el-button @click="form.queryRows.splice(index,1)">删除</el-button></div><el-button @click="form.queryRows.push({key:'',value:''})">添加参数</el-button></div></el-form-item>
      <el-form-item v-if="form.method === 'POST'" label="JSON 请求体"><el-input v-model="form.bodyText" type="textarea" :rows="4" placeholder="{}" /></el-form-item>
      <el-form-item label="认证方式"><el-select v-model="form.auth_type" style="width:100%"><el-option label="无" value="none" /><el-option label="Bearer Token" value="bearer" /><el-option label="Basic Auth" value="basic" /><el-option label="API Key 请求头" value="api_key_header" /><el-option label="自定义请求头" value="custom_headers" /></el-select></el-form-item>
      <el-form-item v-if="form.auth_type === 'bearer'" label="Token"><el-input v-model="form.token" type="password" show-password /></el-form-item>
      <template v-if="form.auth_type === 'basic'"><el-form-item label="用户名"><el-input v-model="form.username" /></el-form-item><el-form-item label="密码"><el-input v-model="form.password" type="password" show-password /></el-form-item></template>
      <template v-if="form.auth_type === 'api_key_header'"><el-form-item label="请求头名称"><el-input v-model="form.header_name" placeholder="X-API-Key" /></el-form-item><el-form-item label="请求头值"><el-input v-model="form.header_value" type="password" show-password /></el-form-item></template>
      <el-form-item v-if="form.auth_type === 'custom_headers'" label="自定义请求头"><div style="width:100%"><div v-for="(row,index) in form.customHeaders" :key="index" style="display:flex;gap:8px;margin-bottom:8px"><el-input v-model="row.key" placeholder="请求头名称" /><el-input v-model="row.value" type="password" placeholder="值" /><el-button @click="form.customHeaders.splice(index,1)">删除</el-button></div><el-button @click="form.customHeaders.push({key:'',value:''})">添加请求头</el-button></div></el-form-item>
      <el-form-item label="分页方式"><el-select v-model="form.paginationType" style="width:100%"><el-option label="无分页" value="NONE" /><el-option label="页码" value="PAGE_NUMBER" /><el-option label="偏移量" value="OFFSET_LIMIT" /><el-option label="游标" value="CURSOR" /></el-select></el-form-item>
      <template v-if="form.paginationType !== 'NONE'"><el-form-item label="分页参数位置"><el-select v-model="form.paginationLocation" style="width:100%"><el-option label="Query" value="query" /><el-option label="JSON Body" value="body" /></el-select></el-form-item><el-form-item label="每页数量"><el-input-number v-model="form.pageSize" :min="1" :max="500" /></el-form-item><el-form-item label="最多页数"><el-input-number v-model="form.maxPages" :min="1" :max="50" /></el-form-item><el-form-item label="数量参数"><el-input v-model="form.sizeParam" /></el-form-item><el-form-item v-if="form.paginationType === 'PAGE_NUMBER'" label="页码参数"><el-input v-model="form.pageParam" /></el-form-item><el-form-item v-if="form.paginationType === 'OFFSET_LIMIT'" label="偏移参数"><el-input v-model="form.offsetParam" /></el-form-item><template v-if="form.paginationType === 'CURSOR'"><el-form-item label="游标参数"><el-input v-model="form.cursorParam" /></el-form-item><el-form-item label="下一页游标路径"><el-input v-model="form.cursorPath" /></el-form-item></template><el-form-item label="总数路径（可选）"><el-input v-model="form.totalPath" /></el-form-item></template>
      <el-form-item label="同步模式"><el-select v-model="form.syncMode" style="width:100%"><el-option label="全量" value="FULL" /><el-option label="增量" value="INCREMENTAL" /></el-select></el-form-item><template v-if="form.syncMode === 'INCREMENTAL'"><el-form-item label="外部更新时间字段路径"><el-input v-model="form.incrementalField" placeholder="meta.updatedAt" /></el-form-item><el-form-item label="请求参数名"><el-input v-model="form.incrementalParam" placeholder="since" /></el-form-item><el-form-item label="参数位置"><el-select v-model="form.incrementalLocation" style="width:100%"><el-option label="Query" value="query" /><el-option label="JSON Body" value="body" /></el-select></el-form-item></template>
    </template>
    <el-form-item v-if="form.type === 'webhook'" label="Webhook 密钥"><el-input v-model="form.webhook_secret" type="password" show-password /></el-form-item>
    <el-button type="primary" :loading="saving" @click="submit">创建连接器</el-button>
  </el-form></div>
</template>
