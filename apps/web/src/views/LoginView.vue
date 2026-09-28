<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const form = reactive({ tenant_code: 'demo', username: 'admin', password: '' })
const loading = ref(false)
const error = ref('')

async function submit() {
  loading.value = true
  error.value = ''
  try {
    await auth.login(form.tenant_code, form.username, form.password)
    const target = typeof route.query.redirect === 'string' && route.query.redirect.startsWith('/') && !route.query.redirect.startsWith('//') ? route.query.redirect : '/dashboard'
    await router.replace(target)
  } catch {
    auth.logout()
    error.value = '登录失败，请检查租户、用户名和密码。'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="login-page">
    <section class="login-card">
      <div class="brand-mark">L</div>
      <p class="eyebrow">LOGISTICS INTELLIGENCE</p>
      <h1>登录 LogiAI Platform</h1>
      <p class="muted">面向现有物流系统的智能能力平台</p>
      <el-form :model="form" label-position="top" @submit.prevent="submit">
        <el-form-item label="租户代码"><el-input v-model="form.tenant_code" autocomplete="organization" /></el-form-item>
        <el-form-item label="用户名"><el-input v-model="form.username" autocomplete="username" /></el-form-item>
        <el-form-item label="密码"><el-input v-model="form.password" type="password" show-password autocomplete="current-password" @keyup.enter="submit" /></el-form-item>
        <p v-if="error" class="error" role="alert">{{ error }}</p>
        <el-button type="primary" native-type="submit" :loading="loading" class="submit">登录</el-button>
      </el-form>
    </section>
  </main>
</template>
