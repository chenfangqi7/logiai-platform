<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { platform } from '../api/platform'
import { errorMessage } from '../utils/errors'

const router = useRouter()
const saving = ref(false)
const form = reactive({ name: '演示 TMS 接口', type: 'rest', base_url: 'http://server:8000/demo/tms/shipments', auth_type: 'none', items_path: '', token: '', header_name: '', header_value: '', webhook_secret: '' })
async function submit() {
  saving.value = true
  const config: Record<string, string> = {}
  for (const key of ['items_path', 'token', 'header_name', 'header_value', 'webhook_secret'] as const) if (form[key]) config[key] = form[key]
  try {
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
    <template v-if="form.type === 'rest'"><el-form-item label="接口 URL"><el-input v-model="form.base_url" /></el-form-item><p class="form-hint">Docker 演示接口：{{ form.base_url }}。部署到其他环境时填写该环境可访问的地址。</p><el-form-item label="数据列表路径（可选）"><el-input v-model="form.items_path" placeholder="例如 data.items" /></el-form-item><el-form-item label="认证方式"><el-select v-model="form.auth_type" style="width:100%"><el-option label="无" value="none" /><el-option label="Bearer Token" value="bearer" /><el-option label="自定义请求头" value="header" /></el-select></el-form-item><el-form-item v-if="form.auth_type === 'bearer'" label="Token"><el-input v-model="form.token" type="password" show-password /></el-form-item><template v-if="form.auth_type === 'header'"><el-form-item label="请求头名称"><el-input v-model="form.header_name" /></el-form-item><el-form-item label="请求头值"><el-input v-model="form.header_value" type="password" show-password /></el-form-item></template></template>
    <el-form-item v-if="form.type === 'webhook'" label="Webhook 密钥"><el-input v-model="form.webhook_secret" type="password" show-password /></el-form-item>
    <el-button type="primary" :loading="saving" @click="submit">创建连接器</el-button>
  </el-form></div>
</template>
