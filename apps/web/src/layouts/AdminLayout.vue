<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const navigation = [
  { path: '/dashboard', label: '仪表盘', icon: '◫' },
  { path: '/connectors', label: '数据接入', icon: '↪' },
  { path: '/shipments', label: '运单中心', icon: '▣' },
  { path: '/exceptions', label: '异常中心', icon: '◇' },
  { path: '/ai', label: 'AI 助手', icon: '✧' },
  { path: '/knowledge', label: '知识库', icon: '▤' },
  { path: '/settings', label: '系统设置', icon: '⚙' },
]
function logout() { auth.logout(); router.replace('/login') }
</script>

<template>
  <div class="shell">
    <aside class="sidebar">
      <div class="sidebar-brand"><span class="brand-mark small">L</span><strong>LogiAI</strong></div>
      <p class="nav-section">工作空间</p>
      <nav aria-label="主导航"><RouterLink v-for="item in navigation" :key="item.path" :to="item.path" class="nav-item"><span class="nav-icon">{{ item.icon }}</span>{{ item.label }}</RouterLink></nav>
      <div class="sidebar-bottom">LOGISTICS INTELLIGENCE</div>
    </aside>
    <div class="main-area">
      <header class="topbar"><span class="topbar-title">LogiAI Platform</span><div><span class="tenant-pill">{{ auth.user?.tenant_code }}</span><span>{{ auth.user?.username }}</span><el-button text @click="logout">退出</el-button></div></header>
      <main class="content"><RouterView /></main>
    </div>
  </div>
</template>
