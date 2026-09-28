<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { platform } from '../api/platform'
import { errorMessage } from '../utils/errors'

const documents = ref<{id:string; title:string; source_type:string; metadata:Record<string,unknown>}[]>([])
const title = ref('')
const content = ref('')
const file = ref<File | null>(null)
const busy = ref(false)
function choose(event: Event) { file.value = (event.target as HTMLInputElement).files?.[0] || null }
async function load() { try { documents.value = await platform.knowledge() } catch (error) { ElMessage.error(errorMessage(error)) } }
async function addText() { busy.value = true; try { await platform.addKnowledgeText(title.value, content.value); title.value = ''; content.value = ''; ElMessage.success('文档已添加'); await load() } catch (error) { ElMessage.error(errorMessage(error)) } finally { busy.value = false } }
async function upload() { if (!file.value) return; busy.value = true; try { await platform.uploadKnowledge(file.value); file.value = null; ElMessage.success('文件已添加'); await load() } catch (error) { ElMessage.error(errorMessage(error)) } finally { busy.value = false } }
async function remove(id: string) { try { await ElMessageBox.confirm('删除此知识文档？', '确认删除'); await platform.deleteKnowledge(id); await load() } catch (error) { if (error !== 'cancel') ElMessage.error(errorMessage(error)) } }
onMounted(load)
</script>

<template>
  <div class="page-heading"><div><p class="eyebrow">KNOWLEDGE BASE</p><h1>知识库</h1><p class="muted">上传制度与 SOP，辅助异常处理建议</p></div></div>
  <div class="two-column"><section class="panel"><div class="panel-title">添加文本知识</div><el-form label-position="top"><el-form-item label="标题"><el-input v-model="title" placeholder="例如：运输异常处理 SOP" /></el-form-item><el-form-item label="内容"><el-input v-model="content" type="textarea" :rows="8" placeholder="输入制度或处理流程" /></el-form-item><el-button type="primary" :loading="busy" @click="addText">保存文本</el-button></el-form></section><section class="panel"><div class="panel-title">上传文件</div><p class="muted">支持 TXT、PDF、DOCX、XLSX，最大 5 MB。</p><input type="file" accept=".txt,.pdf,.docx,.xlsx" @change="choose" /><div class="input-section"><el-button :disabled="!file" :loading="busy" @click="upload">上传并索引</el-button></div></section></div>
  <div class="panel"><div class="panel-title">已收录文档</div><el-table :data="documents" stripe><el-table-column prop="title" label="标题" min-width="260" /><el-table-column prop="source_type" label="类型" width="100" /><el-table-column label="分块" width="100"><template #default="scope">{{ scope.row.metadata?.chunk_count }}</template></el-table-column><el-table-column label="操作" width="100"><template #default="scope"><el-button text type="danger" @click="remove(scope.row.id)">删除</el-button></template></el-table-column></el-table><el-empty v-if="!documents.length" description="暂无知识文档" /></div>
</template>
