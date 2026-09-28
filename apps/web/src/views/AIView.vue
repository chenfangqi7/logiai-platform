<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { platform } from '../api/platform'
import { errorMessage } from '../utils/errors'

interface Message { role: string; content: string; provider?: string | null }
function providerLabel(provider: string | null | undefined) { return provider === 'rules' ? '基于实时数据' : provider ? '模型分析' : '' }
const conversations = ref<{id: string; title: string}[]>([])
const conversationId = ref<string | undefined>()
const messages = ref<Message[]>([])
const input = ref('')
const busy = ref(false)
const suggestions = ['今天有多少异常运单？','今天高风险异常有哪些？','帮我分析今天的异常运输情况。','为什么今天秀山线路延误这么多？']
async function loadList() { try { conversations.value = await platform.conversations() } catch (error) { ElMessage.error(errorMessage(error)) } }
async function open(id: string) { try { const detail = await platform.conversation(id); conversationId.value = id; messages.value = detail.messages } catch (error) { ElMessage.error(errorMessage(error)) } }
function newChat() { conversationId.value = undefined; messages.value = [] }
async function send(question = input.value) { const text = question.trim(); if (!text || busy.value) return; input.value = ''; messages.value.push({role:'user', content:text}); busy.value = true; try { const result = await platform.chat(text, conversationId.value); conversationId.value = result.conversation_id; messages.value.push({role:'assistant', content:result.answer, provider:result.provider}); await loadList() } catch (error) { messages.value.pop(); ElMessage.error(errorMessage(error)) } finally { busy.value = false } }
onMounted(loadList)
</script>

<template>
  <div class="page-heading"><div><p class="eyebrow">AI ASSISTANT</p><h1>物流 AI 助手</h1><p class="muted">基于租户内真实运单和异常数据回答</p></div></div>
  <div class="assistant-layout"><aside class="panel conversation-panel"><el-button type="primary" plain style="width:100%" @click="newChat">+ 新对话</el-button><button v-for="item in conversations" :key="item.id" class="conversation-item" :class="{active: conversationId === item.id}" @click="open(item.id)">{{ item.title }}</button></aside>
    <section class="panel chat-panel"><div class="chat-messages"><div v-if="!messages.length" class="chat-empty"><div class="chat-symbol">✧</div><h2>今天想了解哪些物流情况？</h2><p class="muted">回答会引用当前租户的真实数据；数据不足时会明确说明。</p><div class="suggestions"><el-button v-for="question in suggestions" :key="question" @click="send(question)">{{ question }}</el-button></div></div><div v-for="(message, index) in messages" :key="index" class="bubble-row" :class="message.role"><div class="bubble"><p>{{ message.content }}</p><small v-if="message.provider">{{ providerLabel(message.provider) }}</small></div></div><div v-if="busy" class="muted">正在分析数据…</div></div><div class="chat-input"><el-input v-model="input" type="textarea" :rows="2" placeholder="输入运单、异常或线路问题" @keydown.ctrl.enter="send()" /><el-button type="primary" :loading="busy" @click="send()">发送</el-button></div></section>
  </div>
</template>
