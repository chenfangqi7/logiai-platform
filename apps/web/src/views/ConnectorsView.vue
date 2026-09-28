<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { platform, type Connector } from '../api/platform'
import { errorMessage } from '../utils/errors'

const rows = ref<Connector[]>([])
const loading = ref(false)
async function load() { loading.value = true; try { rows.value = await platform.connectors() } catch (error) { ElMessage.error(errorMessage(error)) } finally { loading.value = false } }
async function remove(id: string) { try { await ElMessageBox.confirm('确定删除此连接器？', '确认删除'); await platform.deleteConnector(id); ElMessage.success('已删除'); await load() } catch (error) { if (error !== 'cancel') ElMessage.error(errorMessage(error)) } }
onMounted(load)
</script>

<template>
  <div class="page-heading"><div><p class="eyebrow">CONNECTOR HUB</p><h1>数据接入</h1><p class="muted">连接现有 TMS / WMS / ERP 数据</p></div><RouterLink to="/connectors/create"><el-button type="primary">新建连接器</el-button></RouterLink></div>
  <div class="panel"><el-table v-loading="loading" :data="rows" stripe><el-table-column prop="name" label="名称" min-width="180" /><el-table-column prop="type" label="类型" width="110" /><el-table-column prop="base_url" label="地址" min-width="230" show-overflow-tooltip /><el-table-column prop="status" label="状态" width="100" /><el-table-column label="操作" width="250"><template #default="scope"><RouterLink :to="`/connectors/${scope.row.id}`"><el-button text type="primary">详情</el-button></RouterLink><RouterLink :to="`/connectors/${scope.row.id}/mapping`"><el-button text>字段映射</el-button></RouterLink><el-button text type="danger" @click="remove(scope.row.id)">删除</el-button></template></el-table-column></el-table><el-empty v-if="!loading && !rows.length" description="暂无连接器" /></div>
</template>
